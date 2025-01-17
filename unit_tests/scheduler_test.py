import unittest
import random
import threading
import time
import os
import sys
basedir = os.path.dirname(os.path.realpath(__file__)).replace("unit_tests", "")
sys.path.append(basedir + 'lib')
sys.path.append(basedir + 'bin')

from still import process_client_config_file, WorkFlow, SpawnerClass
import scheduler as sch
import logging
from task_server import TaskClient
logging.basicConfig(level=logging.DEBUG)


TEST_PORT = 14204


class NullAction(sch.Action):

    def run_remote_task(self):
        return


class FakeDataBaseInterface:

    def __init__(self, nfiles=10):
        self.files = {}
        for i in xrange(nfiles):
            self.files[i] = 'UV_POT'

    def get_obs_status(self, obsnum):
        print("Obs num : %s : Status %s ") % (obsnum, self.files[obsnum])
        return self.files[obsnum]
        #except:
        #    print("Got weird obs num apparently %s") % obsnum

    def list_observations(self):
        files = self.files.keys()
        files.sort()
        return files

    def list_open_observations(self):
        files = self.files.keys()
        files.sort()
        return files

    def get_terminal_obs(self, nfail=5):
        FAILED_OBSNUMS = []
        return FAILED_OBSNUMS

    def get_obs_pid(self, obsnum):
        """
        Jon: had a todo on it when I stole it from dbi
        """
        OBS = self.get_obs(obsnum)
        return False
    def get_obs(self, obsnum):

        return obsnum

    def get_neighbors(self, obsnum):
        n1, n2 = obsnum - 1, obsnum + 1
        if n1 not in self.files:
            n1 = None
        if n2 not in self.files:
            n2 = None
        return (n1, n2)


class TestAction(unittest.TestCase):

    def setUp(self):
        self.files = [1, 2, 3]
        self.still = 0
        self.task = 'UVC'  # Jon : change me : HARDWF
        self.sg = SpawnerClass()
        self.sg.config_file = "still_test_paper.cfg"
        self.wf = WorkFlow()
        process_client_config_file(self.sg, self.wf)

    def test_attributes(self):
        a = sch.Action(self.files[1], self.task, [self.files[0], self.files[2]], self.still, self.wf)
        self.assertEqual(a.task, self.task)
        # XXX could do more here

    def test_priority(self):
        a = sch.Action(self.files[1], self.task, [self.files[0], self.files[2]], self.still, self.wf)
        self.assertEqual(a.priority, 0)
        a.set_priority(5)
        self.assertEqual(a.priority, 5)

    def test_prereqs(self):
        a = sch.Action(self.files[1], self.task, ['UV', None], self.still, self.wf)  # Jon : Fixme HARDWF
        self.assertTrue(a.has_prerequisites())
        # XXX more here

    def test_timeout(self):
        a = NullAction(self.files[1], self.task, ['UV', 'UV'], self.still, self.wf, timeout=100)  # Jon : Fixme HARDWF
        self.assertRaises(AssertionError, a.timed_out)
        t0 = 1000
        a.launch(launch_time=t0)
        self.assertFalse(a.timed_out(curtime=t0))
        self.assertTrue(a.timed_out(curtime=t0 + 110))

    def test_action_cmp(self):
        priorities = range(10)
        # def __init__(self, obs, task, neighbor_status, still, workflow, task_clients=[], timeout=3600.):
        actions = [sch.Action(self.files[1], self.task, [self.files[0], self.files[2]], self.still, self.wf) for p in priorities]
        random.shuffle(priorities)
        for a, p in zip(actions, priorities):
            a.set_priority(p)
        actions.sort(cmp=sch.action_cmp)
        for cnt, a in enumerate(actions):
            self.assertEqual(a.priority, cnt)


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.nfiles = 10
        dbi = FakeDataBaseInterface(self.nfiles)
        self.dbi = dbi
        self.sg = SpawnerClass()
        self.sg.config_file = "still_test_paper.cfg"
        self.wf = WorkFlow()
        process_client_config_file(self.sg, self.wf)

        class FakeAction(sch.Action):
            def run_remote_task(self):
                dbi.files[self.filename] = self.task
        self.FakeAction = FakeAction
        self.task_clients = TaskClient(dbi, 'localhost', self.wf, port=TEST_PORT)

    def test_attributes(self):
        s = sch.Scheduler(self.task_clients, self.wf, nstills=1, actions_per_still=1)
        self.assertEqual(s.launched_actions.keys(), [0])

    def test_get_new_active_obs(self):
        s = sch.Scheduler(self.task_clients, self.wf, nstills=1, actions_per_still=1)
        s.get_new_active_obs(self.dbi)
        for i in xrange(self.nfiles):
            self.assertTrue(i in s.active_obs)

    def test_get_action(self):

        s = sch.Scheduler(self.task_clients, self.wf, nstills=1, actions_per_still=1)
        f = 1
        a = s.get_action(self.dbi, f, ActionClass=self.FakeAction)
        self.assertNotEqual(a, None)  # everything is actionable in this test
        FILE_PROCESSING_LINKS = {'ACQUIRE_NEIGHBORS': 'UVCRE',
                                 'CLEAN_NEIGHBORS': 'UVCRRE_POT',
                                 'CLEAN_NPZ': 'CLEAN_NEIGHBORS',
                                 'CLEAN_UV': 'UVCR',
                                 'CLEAN_UVC': 'ACQUIRE_NEIGHBORS',
                                 'CLEAN_UVCR': 'COMPLETE',
                                 'CLEAN_UVCRE': 'UVCRRE',
                                 'CLEAN_UVCRR': 'CLEAN_NPZ',
                                 'CLEAN_UVCRRE': 'CLEAN_UVCR',
                                 'COMPLETE': None,
                                 'NEW': 'UV_POT',
                                 'NPZ': 'UVCRR',
                                 'NPZ_POT': 'CLEAN_UVCRE',
                                 'UV': 'UVC',
                                 'UVC': 'CLEAN_UV',
                                 'UVCR': 'CLEAN_UVC',
                                 'UVCRE': 'NPZ',
                                 'UVCRR': 'NPZ_POT',
                                 'UVCRRE': 'CLEAN_UVCRR',
                                 'UVCRRE_POT': 'CLEAN_UVCRRE',
                                 'UV_POT': 'UV'}
        self.assertEqual(a.task, FILE_PROCESSING_LINKS[self.dbi.files[f]])  # Jon: FIXME HARDWF # check this links to the next step

    def test_update_action_queue(self):
        s = sch.Scheduler(self.task_clients, self.wf, nstills=1, actions_per_still=1, blocksize=10)
        s.get_new_active_obs(self.dbi)
        s.update_action_queue(self.dbi)
        self.assertEqual(len(s.action_queue), self.nfiles)
        self.assertGreater(s.action_queue[0].priority, s.action_queue[-1].priority)
        for a in s.action_queue:
            self.assertEqual(a.task, 'UV')

    def test_launch(self):
        dbi = FakeDataBaseInterface(10)
        s = sch.Scheduler(self.task_clients, self.wf, nstills=1, actions_per_still=1, blocksize=10)
        s.get_new_active_obs(self.dbi)
        s.update_action_queue(self.dbi)
        a = s.pop_action_queue(0)
        s.launch_action(a)
        self.assertEqual(s.launched_actions[0], [a])
        self.assertNotEqual(a.launch_time, -1)
        self.assertTrue(s.already_launched(a))
        s.update_action_queue(self.dbi)
        self.assertEqual(len(s.action_queue), self.nfiles - 1)  # make sure this action is excluded from list next time

    def test_clean_completed_actions(self):
        dbi = FakeDataBaseInterface(10)
        class FakeAction(sch.Action):
            def run_remote_task(self):
                dbi.files[self.obs] = self.task

        s = sch.Scheduler(self.task_clients, self.wf, nstills=1, actions_per_still=1, blocksize=10)
        s.get_new_active_obs(self.dbi)
        s.update_action_queue(self.dbi, ActionClass=FakeAction)
        a = s.pop_action_queue(0)
        s.launch_action(a)
        self.assertEqual(len(s.launched_actions[0]), 1)
        s.clean_completed_actions(self.dbi)
        self.assertEqual(len(s.launched_actions[0]), 0)

    def test_prereqs(self):
        #        dbi = FakeDataBaseInterface(3)
        a = sch.Action(1, 'UV', ['UV', 'UV'], 0, self.wf)  # Jon : HARDWF
        # a = sch.Action(self.files[1], self.task, ['UV', None], self.still, self.wf)  # Jon : Fixme HARDWF
        self.assertTrue(a.has_prerequisites())
        a = sch.Action(1, 'ACQUIRE_NEIGHBORS', ['UVCR', 'UVCR'], 0, self.wf)  # Jon : HARDWF
        self.assertTrue(a.has_prerequisites())
        a = sch.Action(1, 'ACQUIRE_NEIGHBORS', ['UVCR', 'UV'], 0, self.wf)  # Jon : HARDWF
        self.assertFalse(a.has_prerequisites())

    def test_start(self):
        dbi = FakeDataBaseInterface(10)

        class FakeAction(sch.Action):
            def run_remote_task(self):
                dbi.files[self.obs] = self.task

        def all_done():
            for f in dbi.files:
                if dbi.get_obs_status(f) != 'COMPLETE':
                    return False
            return True

        task_clients = TaskClient(dbi, 'localhost', self.wf, port=TEST_PORT)

        s = sch.Scheduler(task_clients, self.wf, nstills=1, actions_per_still=1, blocksize=10)
#        myscheduler = StillScheduler(task_clients, wf, actions_per_still=ACTIONS_PER_STILL, blocksize=BLOCK_SIZE, nstills=len(STILLS))  # Init scheduler daemon
        t = threading.Thread(target=s.start, args=(dbi, FakeAction), kwargs={'sleeptime': 0})
        t.start()
        tstart = time.time()
        while not all_done() and time.time() - tstart < 1:
            time.sleep(.1)
        s.quit()
        for f in dbi.files:
            self.assertEqual(dbi.get_obs_status(f), 'COMPLETE')

    def test_faulty(self):
        for i in xrange(1):
            dbi = FakeDataBaseInterface(10)

            class FakeAction(sch.Action):
                def __init__(self, f, task, neighbors, still, wf):
                    sch.Action.__init__(self, f, task, neighbors, still, wf, timeout=.01)

                def run_remote_task(self):
                    if random.random() > .5:
                        dbi.files[self.obs] = self.task

            def all_done():
                for f in dbi.files:
                    if dbi.get_obs_status(f) != 'COMPLETE':
                        return False
                return True
            task_clients = TaskClient(dbi, 'localhost', self.wf, port=TEST_PORT)

            s = sch.Scheduler(task_clients, self.wf, nstills=1, actions_per_still=1, blocksize=10)
            t = threading.Thread(target=s.start, args=(dbi, FakeAction), kwargs={'sleeptime': 0})
            t.start()
            tstart = time.time()
            while not all_done() and time.time() - tstart < 10:
                # print s.launched_actions[0][0].obs, s.launched_actions[0][0].task
                # print [(a.obs, a.task) for a in s.action_queue]
                time.sleep(.1)
            s.quit()
            # for f in dbi.files:
            #    print f, dbi.files[f]
            for f in dbi.files:
                self.assertEqual(dbi.get_obs_status(f), 'COMPLETE')

if __name__ == '__main__':
    unittest.main()
