"""Supervisor fault tests with disposable sleeping processes, no AI or personal images."""
import queue,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from local_ai import sessions,supervisor

class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.engine=supervisor.Supervisor();self.engine.cache=Path(self.folder.name)
        sessions.sessions['owner']={'expires':time.time()+60};sessions.sessions['other']={'expires':time.time()+60}
        self.process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        self.messages=queue.Queue();self.engine.worker=self.process;self.engine.messages=self.messages
        self.engine._spawn=lambda:(self.process,self.messages)
        # Unit tests do not depend on the test runner's permission to inspect OS RSS.
        self.rss=patch.object(supervisor.subprocess,'check_output',return_value='0');self.rss.start()
    def tearDown(self):
        self.engine.shutdown();self.rss.stop();self.folder.cleanup();sessions.sessions.clear()
    def wait_finished(self,job):
        for _ in range(100):
            if 'finished' in job and self.engine.worker is None and self.process.poll() is not None:return
            time.sleep(.02)
        self.fail('Supervised job did not finish')
    def test_cancellation_terminates_process_and_purges_owner_only(self):
        job=self.engine.generate('owner',{})
        self.engine.jobs['other-job']={'owner':'other','image':'public fixture','started':time.time()}
        with self.assertRaises(KeyError):self.engine.cancel_job(job['id'],'other')
        result=self.engine.cancel_job(job['id'],'owner');self.wait_finished(job)
        self.assertTrue(result['processingStopped']);self.assertIsNotNone(self.process.poll())
        self.assertNotIn(job['id'],self.engine.jobs);self.assertIn('other-job',self.engine.jobs)
    def test_revocation_terminates_analysis_and_purges_results(self):
        record=self.engine._reserve('owner','analyze',None)
        self.engine.jobs['result']={'owner':'owner','image':'public fixture'}
        result=self.engine.revoke_owner('owner')
        self.assertEqual(result,{'cancelled':1,'purged':1});self.assertTrue(record['cancelled'])
        self.assertIsNotNone(self.process.poll());self.assertFalse(self.engine.jobs)
    def test_hung_job_hits_deadline_and_is_terminated(self):
        with patch.object(supervisor,'GENERATION_TIMEOUT',.03):
            job=self.engine.generate('owner',{});self.wait_finished(job)
        self.assertEqual(job['stage'],'failed');self.assertIn('time limit',job['error']);self.assertIsNotNone(self.process.poll())
    def test_memory_limit_terminates_worker(self):
        with patch.object(supervisor.subprocess,'check_output',return_value=str(supervisor.MAX_RSS_KB+1)):
            job=self.engine.generate('owner',{});self.wait_finished(job)
        self.assertEqual(job['stage'],'failed');self.assertIn('memory',job['error']);self.assertIsNotNone(self.process.poll())
    def test_crashed_worker_never_becomes_a_preview(self):
        self.messages.put({'kind':'closed'});job=self.engine.generate('owner',{});self.wait_finished(job)
        self.assertEqual(job['stage'],'failed');self.assertIsNone(job['image']);self.assertIsNotNone(self.process.poll())
    def test_invalid_worker_reply_never_becomes_a_preview(self):
        self.messages.put({'kind':'result','image':'https://unexpected.example/image'});job=self.engine.generate('owner',{});self.wait_finished(job)
        self.assertEqual(job['stage'],'failed');self.assertIsNone(job['image']);self.assertIsNotNone(self.process.poll())
    def test_queue_rejects_second_operation(self):
        self.engine._reserve('owner','analyze',None)
        with self.assertRaises(supervisor.Busy):self.engine.generate('other',{})
    def test_revocation_before_exchange_cannot_restart_a_worker(self):
        record=self.engine._reserve('owner','analyze',None);self.engine.revoke_owner('owner')
        with patch.object(self.engine,'_spawn') as spawn:
            with self.assertRaises(supervisor.Stopped):self.engine._exchange(record,{'operation':'analyze','image':'public fixture'})
            spawn.assert_not_called()
    def test_termination_failure_retains_worker_and_disables_processing(self):
        self.engine._reserve('owner','analyze',None);self.engine.sandbox_ready=True
        self.engine.jobs['result']={'owner':'owner','image':'public fixture'}
        with patch.object(self.process,'terminate',side_effect=PermissionError('controlled OS denial')):
            with self.assertRaises(supervisor.WorkerFailure):self.engine.revoke_owner('owner')
        self.assertIs(self.engine.worker,self.process);self.assertFalse(self.engine.sandbox_ready);self.assertFalse(self.engine.jobs)
        self.assertTrue(self.engine.current['cancelled']);self.assertIsNone(self.process.poll())
        self.engine.revoke_owner('owner');self.assertIsNotNone(self.process.poll())

