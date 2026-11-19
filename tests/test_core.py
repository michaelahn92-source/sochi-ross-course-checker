import io
import json
import unittest
from core import ROOT, add_term, codes, reconcile, schedule_rows, workbook_rows

MODEL=json.loads((ROOT/'models/ridge.json').read_text())


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.demo=json.loads((ROOT/'demo.json').read_text())

    def test_real_registrar_headers_and_subject(self):
        csv=b'Term,Subject,Catalog Nbr,Section,Course Title\nWinter 2027,Architecture (ARCH),212,001,Understand Arch\n'
        self.assertEqual(schedule_rows(csv,'Winter 2027')[0]['code'],'ARCH 212')

    def test_term_mismatch_and_html_rejected(self):
        with self.assertRaises(ValueError):schedule_rows(b'<html>Login</html>','Winter 2027')
        with self.assertRaises(ValueError):schedule_rows(b'subject,catalog_number,title,term\nBA,320,Course,Fall 2026\n','Winter 2027')

    def test_preserves_seasonal_terms_and_reactivation(self):
        r=reconcile(self.demo['courses'],self.demo['schedule'],'Winter 2027',MODEL)
        self.assertEqual(r['suggestions'][0]['proposed_term'],'Fall 26, Winter 27')
        self.assertEqual(r['suggestions'][1]['action'],'Reactivate course')
        self.assertEqual(r['suggestions'][1]['proposed_term'],'Winter 27')

    def test_missing_does_not_mean_discontinued(self):
        r=reconcile(self.demo['courses'],[],'Winter 2027',MODEL)
        self.assertTrue(all(x['proposed_term']==x['term'] for x in r['suggestions']))
        self.assertFalse(any(x['action']=='Move to Not Current' for x in r['suggestions']))

    def test_special_topics_do_not_silently_update(self):
        r=reconcile(self.demo['courses'],self.demo['schedule'],'Winter 2027',MODEL)
        self.assertEqual(r['suggestions'][6]['action'],'Review topic / title')
        self.assertEqual(r['suggestions'][6]['proposed_term'],'Fall 26')

    def test_no_source_mutation_and_discovery(self):
        before=json.dumps(self.demo)
        r=reconcile(self.demo['courses'],self.demo['schedule'],'Winter 2027',MODEL)
        self.assertEqual(json.dumps(self.demo),before)
        self.assertEqual(r['discovery'][0]['code'],'ENVIRON 999')

    def test_empty_and_bad_workbook_rejected(self):
        with self.assertRaises(ValueError):workbook_rows(b'not xlsx','bad')

    def test_case_and_duplicate_terms(self):
        self.assertEqual(codes(' SW 505 '),[('SW','505')])
        self.assertEqual(add_term('Fall 26, Winter 27','Winter 2027'),'Fall 26, Winter 27')

    def test_wsgi_health_demo_and_invalid_upload(self):
        from app import application
        def call(path,method='GET',payload=None):
            body=json.dumps(payload).encode() if payload else b''
            status=[]
            data=b''.join(application({'PATH_INFO':path,'REQUEST_METHOD':method,'CONTENT_LENGTH':str(len(body)),'CONTENT_TYPE':'application/json','wsgi.input':io.BytesIO(body)},lambda s,h:status.append(s)))
            return status[0],json.loads(data)
        self.assertEqual(call('/health')[0],'200 OK')
        self.assertTrue(call('/demo')[1]['demo'])
        self.assertEqual(call('/analyze','POST',{'term':'Winter 2027','workbooks':[]})[0],'400 Bad Request')
        self.assertEqual(call('/missing')[0],'404 Not Found')


if __name__=='__main__':unittest.main()
