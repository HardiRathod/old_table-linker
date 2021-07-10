import pandas as pd
from tl.features.utility import Utility
from tl.exceptions import RequiredInputParameterMissingException

HC_CANDIDATE = 'hc_candidate'


class SemanticsFeature(object):
    def __init__(self, output_column, feature_file, feature_name, total_docs, pagerank_column, retrieval_score_column,
                 input_file=None, df=None):

        if df is None and input_file is None:
            raise RequiredInputParameterMissingException(
                'One of the input parameters is required: {} or {}'.format("input_file", "df"))

        if input_file is not None:
            i_df = pd.read_csv(input_file)
            i_df['kg_id'].fillna("", inplace=True)
            self.input_df = i_df[i_df['kg_id'] != ""]

        elif df is not None:
            self.input_df = df

        self.output_col_name = output_column
        self.pagerank_column = pagerank_column
        self.retrieval_score_column = retrieval_score_column
        self.N = float(total_docs)
        self.utils = Utility()

        self.multiply_pgr_rts()
        self.feature_dict, self.feature_count_dict = self.utils.build_qnode_feature_dict(feature_file, feature_name)
        self.feature_idf_dict = self.utils.calculate_idf_features(self.feature_count_dict, self.N)

        self.feature_name = feature_name
        self.hc_candidates = self.find_hc_candidates()
        self.hc_classes = self.create_hc_classes_set()

    def create_hc_classes_set(self):
        hc_classes = set()
        for candidate in self.hc_candidates:
            hc_classes.update(self.feature_dict.get(candidate, []))
        return hc_classes

    def find_hc_candidates(self):
        self.label_high_confidence_candidates()
        data = self.input_df[self.input_df[HC_CANDIDATE] == 1]
        hc_candidates = set(data['kg_id'])
        return hc_candidates

    def label_high_confidence_candidates(self):
        data = self.input_df
        data.loc[:, HC_CANDIDATE] = 0
        data.loc[data['method'] == 'exact-match', HC_CANDIDATE] = 1
        grouped = data.groupby(['column', 'row'])
        table_lens = {}

        for key, gdf in grouped:
            if key[0] not in table_lens:
                table_lens[key[0]] = 0
            table_lens[key[0]] += 1
            top_fuzzy_match = gdf[gdf['method'] == 'fuzzy-augmented']['pgr_rts'].max()
            print(key, top_fuzzy_match)
            # max_ids =
            data.loc[data['pgr_rts'] == top_fuzzy_match, HC_CANDIDATE] = 1
            # data.iloc[max_ids, data.columns.get_loc("hc_candidate")] = 1
        self.input_df = data
        self.table_lengths = table_lens

    def multiply_pgr_rts(self):
        # create a new feature by multiplying the pagerank and the retrieval score
        scores = []

        for pagerank, retrieval_score in zip(self.input_df[self.pagerank_column],
                                             self.input_df[self.retrieval_score_column]):
            scores.append(pagerank * retrieval_score)

        self.input_df['pgr_rts'] = scores

    def compute_semantic_feature(self):

        top_5_features = []
        scores = []
        top_5_col_name = f"top5_{self.output_col_name}"

        candidate_x_i, alpha_j = self.compute_xi_alphaj()
        hc_classes_idf = self.utils.normalize_idf_high_confidence_classes(self.input_df, HC_CANDIDATE,
                                                                          self.feature_dict, self.feature_idf_dict)

        for _qnode, column, row, hc_candidate in zip(self.input_df['kg_id'], self.input_df['column'],
                                                     self.input_df['row'], self.input_df[HC_CANDIDATE]):

            top_5_features_candidate = {}

            _candidate_classes = self.feature_dict.get(_qnode, [])
            if hc_candidate == 0:
                scores.append(0.0)
                top_5_features.append("")
            else:
                _score = hc_candidate * sum([
                    candidate_x_i[column][row].get(_qnode, dict()).get(cc, 0.0) *
                    alpha_j[column].get(cc, 0.0) *
                    hc_classes_idf[column].get(cc, 0.0)
                    for cc in self.feature_dict.get(_qnode, [])])
                for cc in self.feature_dict.get(_qnode, []):
                    top_5_features_candidate[cc] = hc_classes_idf[column].get(cc, 0.0)

                scores.append(_score)
                top_5_features.append("|".join([f"{k}:{'{:.3f}'.format(v)}" for k, v in
                                                sorted(top_5_features_candidate.items(),
                                                       key=lambda x: x[1], reverse=True)[:5]]))
        self.input_df[self.output_col_name] = scores
        self.input_df[top_5_col_name] = top_5_features
        return self.input_df

    def compute_xi_alphaj(self) -> (dict, dict):
        data = self.input_df[self.input_df[HC_CANDIDATE] == 1]

        classes_count = {}
        candidate_x_i = {}
        alpha_j = {}
        columns_df = data.groupby(['column'])

        for column, column_df in columns_df:
            classes_count[column] = {}
            rows_df = column_df.groupby(['row'])
            for row_id, row_df in rows_df:
                classes_count[column][row_id] = {}
                for _qnode, in zip(row_df['kg_id']):
                    candidate_classes = self.feature_dict.get(_qnode, [])
                    for cc in candidate_classes:
                        if _qnode not in classes_count[column][row_id]:
                            classes_count[column][row_id][_qnode] = {}

                        if cc not in classes_count[column][row_id][_qnode]:
                            classes_count[column][row_id][_qnode][cc] = 0
                        classes_count[column][row_id][_qnode][cc] += 1

        for c in classes_count:
            c_d = classes_count[c]
            candidate_x_i[c] = {}
            for r in c_d:
                candidate_x_i[c][r] = {}
                r_d = c_d[r]
                class_count = {}
                for candidate in r_d:
                    candidate_x_i[c][r][candidate] = {}
                    classes = r_d[candidate]
                    for classs in classes:
                        if classs not in class_count:
                            class_count[classs] = 0
                        class_count[classs] += 1
                    for classs in classes:
                        candidate_x_i[c][r][candidate][classs] = 1 / class_count[classs]

        for c in candidate_x_i:
            c_d = candidate_x_i[c]
            alpha_j[c] = {}
            for r in c_d:
                r_d = c_d[r]
                for candidate in r_d:
                    classes = r_d[candidate]
                    for cc in classes:
                        if cc not in alpha_j[c]:
                            alpha_j[c][cc] = classes[cc]
                        else:
                            alpha_j[c][cc] += classes[cc]
        for column in alpha_j:
            for cc in alpha_j[column]:
                alpha_j[column][cc] = alpha_j[column][cc] / self.table_lengths[column]
        return candidate_x_i, alpha_j