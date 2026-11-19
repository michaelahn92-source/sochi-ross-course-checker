import json
import unittest
from core import ROOT
from categories import predict,attach

class CategoryTests(unittest.TestCase):
    def setUp(self):self.model=json.loads((ROOT/'models/categories.json').read_text())
    def test_multilabel_predictions_use_existing_taxonomy(self):
        r=predict({'code':'ENVIRON 480','title':'Climate Change and Sustainability'},self.model)
        self.assertIn('Climate & Sustainability',r['categories']['Subject']['labels'])
        for field,p in r['categories'].items():
            self.assertTrue(set(p['labels']) <= set(self.model['fields'][field]['labels']))
            self.assertTrue(p['review_required'])
    def test_unseen_text_abstains(self):
        r=predict({'title':'qxzvwyrpq'},self.model)
        self.assertFalse(r['text_coverage'])
        self.assertTrue(all(not p['labels'] for p in r['categories'].values()))
    def test_attach_preserves_existing_categories(self):
        r={'suggestions':[{'title':'Climate Change','tags':'Existing label'}],'discovery':[]}
        attach(r,self.model)
        self.assertEqual(r['suggestions'][0]['tags'],'Existing label')
        self.assertIn('suggested_subject',r['suggestions'][0])
