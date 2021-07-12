import unittest
import pandas as pd
from pathlib import Path
from tl.features.context_match import MatchContext

parent_path = Path(__file__).parent


class TestContextMatch(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestContextMatch, self).__init__(*args, **kwargs)
        self.output_column_name = "weighted_context_score"
        self.input_file_path = '{}/data/unit_test.csv'.format(parent_path)
        self.context_file_path = '{}/data/unit_test_context.tsv'.format(parent_path)
        self.custom_context_path = '{}/data/custom_context.tsv.gz'.format(parent_path)
        self.kwargs = {'similarity_string_threshold': 0.90, 'similarity_quantity_threshold': 0.80,
                       'string_separator': ",", 'output_column': self.output_column_name}

    def test_combination_types_of_input(self):
        # the input file contains varied set of inputs ranging from
        # quantity as numbers, floats and badly formatted numbers, dates and strings with separators.
        obj_1 = MatchContext(self.input_file_path, self.kwargs, self.context_file_path, custom_context_path=None)
        odf = obj_1.process_data_by_column()
        odf.to_csv('{}/data/result_test_1.csv'.format(parent_path), index=False)
        columns = odf.columns
        # The context-score's should not be all 0).
        distinct_context_score_values = odf[self.output_column_name].unique().tolist()
        # Check for one row : Red Dead Redemption Q548203
        node_context_score = odf[odf['kg_id'] == 'Q548203'][self.output_column_name].values.tolist()[0]
        self.assertTrue(len(distinct_context_score_values) > 1)
        self.assertTrue(self.output_column_name in columns)
        self.assertTrue(node_context_score == 1.0)

    def test_for_custom_context_file(self):
        # The custom file contains the property Pcoauthor and should therefore match for column 7's some of the qnodes.
        obj_2 = MatchContext(self.input_file_path, self.kwargs, custom_context_path=self.custom_context_path,
                             context_path=None)
        odf = obj_2.process_data_by_column()
        odf.to_csv('{}/data/result_test_2.csv'.format(parent_path), index=False)
        columns = odf.columns
        # Check if the score for a researcher is greater than 0. 
        researcher_val = odf[odf['kg_id'] == 'Q91463330'][self.output_column_name].values.tolist()
        # researcher_prop_value contains the value for the properties matched.
        researcher_prop_value = odf[odf['kg_id'] == 'Q91463330']['context_property'].values.tolist()
        # The custom context file contains Pcoauthor as property.
        researcher_prop_value_list = researcher_prop_value[0].split("|")
        self.assertTrue(researcher_val[0] > 0)
        self.assertTrue('Pcoauthor' in researcher_prop_value_list)
        self.assertTrue('context_similarity' in columns)
        self.assertTrue('context_property' in columns)
        
    def test_for_string_separators(self):
        # We will check for results with string separator ;
        kwargs = self.kwargs
        kwargs['string_separator'] = ";"
        obj_3 = MatchContext(self.input_file_path, kwargs, custom_context_path=self.custom_context_path,
                             context_path=None)
        odf = obj_3.process_data_by_column()
        odf.to_csv('{}/data/result_test_3.csv'.format(parent_path), index=False)
        # Check for qnode researcher
        node_property = odf[odf['kg_id'] == 'Q91463330']['context_property'].values.tolist()[0]
        # The custom context file contains Pcoauthor as property.
        researcher_prop_value_list = node_property.split("|")
        node_similarity = odf[odf['kg_id'] == 'Q91463330']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q91463330'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_similarity.split("|")[2]  == '1.0')
        self.assertTrue(researcher_prop_value_list[2] == 'Pcoauthor')
        self.assertTrue(node_context_score == 0.5)
        

    def test_for_quantity_match(self):
        kwargs = self.kwargs
        kwargs['similarity_quantity_threshold'] = 1
        obj_4 = MatchContext(self.input_file_path, kwargs, context_path=self.context_file_path)
        odf = obj_4.process_data_by_column()
        odf.to_csv('{}/data/result_test_4.csv'.format(parent_path), index=False)
        # Check for the United States. 
        # The property should match to P3259 with similariy 1.
        node_property = odf[odf['kg_id'] == 'Q30']['context_property'].values.tolist()[0]
        node_similarity = odf[odf['kg_id'] == 'Q30']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q30'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_property == 'P3529')
        self.assertTrue(node_similarity == "1.0")
        self.assertTrue(node_context_score == 0.5)
        
    def test_for_item_match(self):
        kwargs = self.kwargs
        kwargs['similarity_string_threshold'] = 0.85
        obj_5 = MatchContext(self.input_file_path, kwargs, context_path=self.context_file_path)
        odf = obj_5.process_data_by_column()
        odf.to_csv('{}/data/result_test_5.csv'.format(parent_path), index=False)
        # Check for the Bioshock series. 
        # The property P400 should match with similariy 0.87 for the context field Windows ..
        node_property = odf[odf['kg_id'] == 'Q4914658']['context_property'].values.tolist()[0]
        node_similarity = odf[odf['kg_id'] == 'Q4914658']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q4914658'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_property.split("|")[2] == 'P400')
        self.assertTrue(node_similarity.split("|")[2] == "0.875")
        self.assertTrue(node_context_score >= 0.87)
        
    def test_for_date_match(self):
        obj_6 = MatchContext(self.input_file_path, self.kwargs, context_path=self.context_file_path)
        odf = obj_6.process_data_by_column()
        odf.to_csv('{}/data/result_test_6.csv'.format(parent_path), index=False)
        # Check for the Bioshock series. 
        # The property P400 should match with similariy 0.87 for the context field Windows ..
        node_property = odf[odf['kg_id'] == 'Q102395995']['context_property'].values.tolist()[0]
        node_similarity = odf[odf['kg_id'] == 'Q102395995']['context_similarity'].values.tolist()[0]
        node_context_score = odf[odf['kg_id'] == 'Q102395995'][self.output_column_name].values.tolist()[0]
        self.assertTrue(node_property.split("|")[1] == 'P577')
        self.assertTrue(node_similarity.split("|")[1] == "1.0")
        self.assertTrue(node_context_score == 1.0)