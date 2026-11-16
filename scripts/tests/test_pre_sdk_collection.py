"""Prove collection continues and every failure still prevents application compilation."""
import ast,contextlib,io,json,os,shlex,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pre_sdk_check_collection import CheckCollection
from validate_private_temporary_transcription import save_failed_fixture
ROOT=Path(__file__).resolve().parents[2]


class CollectionTests(unittest.TestCase):
    def test_all_independent_checks_run_and_gate_fails(self):
        c=CheckCollection();seen=[]
        def bad():seen.append('bad');raise RuntimeError('native failure')
        with contextlib.redirect_stdout(io.StringIO()):
            c.run('bad',bad);value=c.run('next',lambda:seen.append('next') or {'status':'passed'})
        self.assertEqual(seen,['bad','next']);self.assertEqual(value,{'status':'passed'})
        with self.assertRaises(SystemExit):c.require_success()

    def test_success_results_are_not_replaced(self):
        c=CheckCollection();value=[{'mode':'debug','exit_code':0}]
        self.assertIs(c.run('pass',lambda:value),value);c.require_success()

    def test_system_exit_is_failed_even_when_zero(self):
        for code in [0,1]:
            c=CheckCollection()
            def stop():raise SystemExit(code)
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(c.run('exit',stop,fallback=[]),[])
            with self.assertRaises(SystemExit):c.require_success()

    def test_user_interrupt_is_not_swallowed(self):
        c=CheckCollection()
        def stop():raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):c.run('interrupt',stop)

    def test_failure_report_written_before_final_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'failures.json';c=CheckCollection(p)
            def bad():raise ValueError('original diagnostic')
            with contextlib.redirect_stdout(io.StringIO()):c.run('native',bad)
            value=json.loads(p.read_text());self.assertEqual(value['status'],'failed');self.assertIn('original diagnostic',value['failed_checks'][0]['traceback'])

    def test_generated_program_and_diagnostics_are_retained(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.swift';p.write_text('public source fixture')
            with mock.patch.dict(os.environ,{'GITHUB_ACTIONS':'true','RUNNER_TEMP':d}):
                save_failed_fixture(p,'../fixture','optimized','runtime',subprocess.CompletedProcess([],96,'stdout','diagnostic'))
            root=Path(d)/'nagramix-test-failures';self.assertEqual(len(list(root.glob('*.swift'))),1)
            self.assertEqual(next(root.glob('*.swift')).read_text(),p.read_text())
            self.assertEqual(json.loads(next(root.glob('*.json')).read_text())['exit_code'],96)

    def test_all_early_api_and_fixture_calls_are_collected(self):
        tree=ast.parse((ROOT/'scripts/validate_release_095_apple_preflight.py').read_text())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        collected={id(x) for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='checks' and n.func.attr=='run' for x in ast.walk(n.args[1])}
        required=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and (n.func.id=='execute' or n.func.id.endswith('_check'))]
        self.assertEqual(len(required),60);self.assertTrue(all(id(n) in collected for n in required))
        self.assertIn('checks.require_success()',ast.unparse(main))

    def test_workflow_runs_later_checks_but_never_compiles_after_failure(self):
        text=(ROOT/'.github/workflows/build-unsigned-ipa.yml').read_text()
        step=text.split('      - name: Проверить геометрию тестов на Apple Swift\n',1)[1].split('      - name:',1)[0]
        body='\n'.join(line[10:] for line in step.split('        run: |\n',1)[1].splitlines())
        calls=[line for line in body.splitlines() if line.startswith('python3 scripts/')]
        self.assertEqual(len(calls),5);self.assertTrue(all(line.endswith(' || nagramix_pre_sdk_failed=1') for line in calls))
        for failing in [-1,*range(5)]:
            with self.subTest(failing=failing),tempfile.TemporaryDirectory() as d:
                script=body
                for line in body.splitlines():
                    if line.startswith('export '):script=script.replace(line,':',1)
                for index,line in enumerate(calls):
                    code='from pathlib import Path;import os,sys;p=Path(os.environ["TRACE"]);p.write_text((p.read_text() if p.exists() else "")+'+repr(str(index))+');sys.exit('+str(1 if index==failing else 0)+')'
                    script=script.replace(line,'python3 -c '+shlex.quote(code)+' || nagramix_pre_sdk_failed=1',1)
                script+='\npython3 -c '+shlex.quote('from pathlib import Path;import os;Path(os.environ["COMPILE_SENTINEL"]).touch()')+'\n'
                env=dict(os.environ,TRACE=d+'/trace',COMPILE_SENTINEL=d+'/compile')
                p=subprocess.run(['bash','-euo','pipefail','-c',script],env=env,capture_output=True,text=True)
                self.assertEqual((Path(d)/'trace').read_text(),'01234')
                self.assertEqual(p.returncode,0 if failing==-1 else 1)
                self.assertEqual((Path(d)/'compile').exists(),failing==-1)


if __name__=='__main__':unittest.main()
