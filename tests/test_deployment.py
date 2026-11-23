import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('deploy_agent',ROOT/'deploy/auto_update.py')
agent=importlib.util.module_from_spec(spec);spec.loader.exec_module(agent)


class ArchiveTests(unittest.TestCase):
    def test_path_escape_and_links_are_rejected(self):
        for name in ['/etc/passwd','../secrets','static/../../key']:
            with self.assertRaises(RuntimeError):agent.valid_member(tarfile.TarInfo(name))
        for kind in [tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.CHRTYPE]:
            info=tarfile.TarInfo('foo');info.type=kind
            with self.assertRaises(RuntimeError):agent.valid_member(info)

    def test_data_and_secrets_are_excluded_from_deploy(self):
        for name in ['zenthex.db','nested/users.sqlite3','.env','.env.prod','uploads/plan.png','static/models/model.glb','auth/__pycache__/hash.pyc','key.pem']:
            self.assertFalse(agent.valid_member(tarfile.TarInfo(name)),name)
        self.assertTrue(agent.valid_member(tarfile.TarInfo('auth/hash.py')))
        self.assertTrue(agent.valid_member(tarfile.TarInfo('.env.example')))

    def test_prepare_refuses_root(self):
        with patch.object(agent.os,'geteuid',return_value=0):
            with self.assertRaises(RuntimeError):agent.prepare(Path('/unused'),'a'*40,Path('/unused'))


class StatusContractTests(unittest.TestCase):
    def status(self):
        from modules_status import module_status
        from trading import router as routes
        with patch.dict(agent.os.environ, {'ZENTHEX_ENABLE_LIVE_TRADING':'false'}), patch.object(routes, 'ENGINE_TASK', None), patch.object(routes.bot_state, 'state', 'STOPPED'), patch.object(routes.bot_state, 'held_btc', 0), patch.object(routes.bot_state, 'avg_buy_price', 0):
            return module_status()

    def test_actual_server_response_matches_deployment_reader(self):
        payload=self.status()
        self.assertIn('deployment',payload)
        self.assertNotIn('deployment',payload['studio'])
        self.assertFalse(agent.deployment_blocked(payload))

    def test_previously_shipped_nested_response_is_supported(self):
        payload=self.status()
        payload['studio']['deployment']=payload.pop('deployment')
        self.assertFalse(agent.deployment_blocked(payload))
        payload['studio']['deployment']['studioBusy']=True
        self.assertTrue(agent.deployment_blocked(payload))

    def test_unknown_or_incomplete_response_never_means_idle(self):
        for payload in [None,{}, {'deployment':{}}, {'studio':{'deployment':{}}},
                        {'deployment':{'engineState':'STOPPED','engineTaskActive':False,'hasPosition':False},'trading':{'liveEnabled':False}}]:
            with self.subTest(payload=payload),self.assertRaises(agent.DeployDeferred):
                agent.deployment_blocked(payload)
        payload=self.status();payload['deployment']['hasPosition']='false'
        with self.assertRaises(agent.DeployDeferred):agent.deployment_blocked(payload)

    def test_each_activity_prevents_deployment_in_real_response(self):
        for key,value in [('engineState','SCANNING'),('engineTaskActive',True),('hasPosition',True),('studioBusy',True)]:
            payload=self.status();payload['deployment'][key]=value
            self.assertTrue(agent.deployment_blocked(payload))

    def test_legacy_status_requires_explicit_stop_and_zero_holdings(self):
        payload={'state':'STOPPED','isRunning':False,'heldBtc':0,'avgBuyPrice':0}
        self.assertFalse(agent.legacy_blocked(payload))
        self.assertTrue(agent.legacy_blocked({**payload,'heldBtc':0.1}))
        for value in [None, {}, {'state':'STOPPED'}, {**payload,'heldBtc':float('nan')}]:
            with self.assertRaises(agent.DeployDeferred):agent.legacy_blocked(value)


class DeferTests(unittest.TestCase):
    def test_armed_server_never_fetches_or_restarts(self):
        with patch.object(agent,'read_env',return_value={'ZENTHEX_ENABLE_LIVE_TRADING':'true'}),patch.object(agent,'command') as command:
            with self.assertRaises(agent.DeployDeferred):agent.idle_check()
            command.assert_not_called()

    def test_active_runtime_is_checked_even_if_env_file_is_false(self):
        with patch.object(agent,'read_env',return_value={'ZENTHEX_ENABLE_LIVE_TRADING':'false'}),patch.object(agent,'command',return_value='123'),patch.object(Path,'read_bytes',return_value=b'ZENTHEX_ENABLE_LIVE_TRADING=true\0'):
            with self.assertRaises(agent.DeployDeferred):agent.idle_check()

    def test_running_engine_or_studio_job_prevents_promotion(self):
        state={'engineState':'STOPPED','engineTaskActive':False,'hasPosition':False,'studioBusy':False}
        for key,value in [('engineState','HOLDING'),('engineTaskActive',True),('hasPosition',True),('studioBusy',True)]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as temp:
                config={'ZENTHEX_ENABLE_LIVE_TRADING':'false','ZENTHEX_TRADING_STATE_DIR':temp}
                with patch.object(agent,'read_env',return_value=config),patch.object(agent,'command',return_value='123'),patch.object(Path,'read_bytes',return_value=b'ZENTHEX_ENABLE_LIVE_TRADING=false\0'),patch.object(agent,'json_get',return_value={'deployment':{**state,key:value},'trading':{'liveEnabled':False}}):
                    with self.assertRaises(agent.DeployDeferred):agent.idle_check()

    def test_backup_does_not_create_missing_production_database(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'absent.db'
            with self.assertRaises(RuntimeError):agent.private_backup({'ZENTHEX_DATABASE_URL':'sqlite:///'+str(path)})
            self.assertFalse(path.exists())

    def test_switch_can_restore_previous_release(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(agent,'APP',Path(temp)/'app'):
            first=Path(temp)/'first';first.mkdir()
            second=Path(temp)/'second';second.mkdir()
            agent.switch(first);self.assertEqual(agent.APP.resolve(),first)
            agent.switch(second);self.assertEqual(agent.APP.resolve(),second)
            agent.switch(first);self.assertEqual(agent.APP.resolve(),first)


class PromoteTests(unittest.TestCase):
    def test_failed_health_restores_old_code_and_preserves_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);app=root/'app';app.mkdir()
            (app/'old.txt').write_text('old')
            (app/'uploads').mkdir();(app/'uploads/keep.png').write_bytes(b'keep')
            candidate=root/'candidate';candidate.mkdir();(candidate/'uploads').mkdir()
            (candidate/'static/models').mkdir(parents=True)
            guard=root/'guard'
            with patch.object(agent,'APP',app),patch.object(agent,'RELEASES',root/'releases'),patch.object(agent,'SHARED_STUDIO',root/'shared'),patch.object(agent,'idle_check',return_value=({},guard)),patch.object(agent,'private_backup',return_value=root/'backup'),patch.object(agent,'command') as command,patch.object(agent,'json_get',return_value={'status':'wrong'}),patch.object(agent.time,'sleep'),patch.object(agent.os,'chown'),patch.object(agent.pwd,'getpwnam',return_value=Mock(pw_uid=1000)),patch.object(agent.grp,'getgrnam',return_value=Mock(gr_gid=1000)):
                with self.assertRaises(RuntimeError):agent.promote(candidate,'a'*40)
                self.assertEqual((app/'old.txt').read_text(),'old')
                self.assertEqual((root/'shared/uploads/keep.png').read_bytes(),b'keep')
                self.assertEqual(command.call_args.args[0],['systemctl','restart','zenthex'])
                agent.os.chown.assert_any_call(root/'releases',0,1000)
                self.assertEqual((root/'releases').stat().st_mode & 0o777,0o750)

    def test_retry_preserves_inactive_failed_release_and_installs_new_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);app=root/'app';app.mkdir();(app/'old.txt').write_text('old')
            candidate=root/'candidate';candidate.mkdir();(candidate/'new.txt').write_text('new')
            releases=root/'releases';releases.mkdir()
            revision='a'*40;failed=releases/revision;failed.mkdir();(failed/'failure.txt').write_text('preserve')
            guard=root/'guard'
            with patch.object(agent,'APP',app),patch.object(agent,'RELEASES',releases),patch.object(agent,'SHARED_STUDIO',root/'shared'),patch.object(agent,'STATE',root/'state'),patch.object(agent,'idle_check',return_value=({},guard)),patch.object(agent,'private_backup',return_value=root/'backup'),patch.object(agent,'command'),patch.object(agent,'json_get',side_effect=[{'status':'ok','release':revision},{'trading':{'liveEnabled':False}}]),patch.object(agent.os,'chown'),patch.object(agent.pwd,'getpwnam',return_value=Mock(pw_uid=1000)),patch.object(agent.grp,'getgrnam',return_value=Mock(gr_gid=1000)):
                agent.promote(candidate,revision)
            self.assertEqual((app/'new.txt').read_text(),'new')
            quarantined=list(releases.glob('failed-'+revision+'-*'))
            self.assertEqual(len(quarantined),1)
            self.assertEqual((quarantined[0]/'failure.txt').read_text(),'preserve')
