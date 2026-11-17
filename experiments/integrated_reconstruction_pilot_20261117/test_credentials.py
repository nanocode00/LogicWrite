"""Credential fixtures are invented strings; no user's dotenv is read by tests."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('credential_pilot',HERE/'run.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_environment_precedes_files_without_opening_them(self):
        with patch.dict(os.environ,{'OPENROUTER_API_KEY':'fixture-environment'},clear=True):
            with patch.object(Path,'read_text',side_effect=AssertionError('must not read')):
                key,source=p.load_api_key([self.root/'.env'])
        self.assertEqual(key,'fixture-environment');self.assertEqual(source,'environment')

    def test_only_selected_key_no_shell_or_expansion(self):
        path=self.root/'.env'
        path.write_text('OTHER=$(touch /tmp/forbidden)\nexport OPENROUTER_API_KEY="fixture-value" # comment\n')
        with patch.dict(os.environ,{},clear=True):
            key,source=p.load_api_key([path])
            self.assertNotIn('OTHER',os.environ)
        self.assertEqual(key,'fixture-value')
        self.assertEqual(source,str(path))

    def test_empty_duplicate_multiline_and_substitution_fail(self):
        for text in ['OPENROUTER_API_KEY=\n','OPENROUTER_API_KEY=a\nOPENROUTER_API_KEY=b\n',
                     'OPENROUTER_API_KEY="a\nb"\n','OPENROUTER_API_KEY=$(echo bad)\n']:
            path=self.root/'.env';path.write_text(text)
            with patch.dict(os.environ,{},clear=True),self.assertRaises(p.Blocked):
                p.load_api_key([path])

    def test_precedence_experiment_then_worktree_then_primary(self):
        paths=[self.root/x/'.env' for x in ['experiment','worktree','primary']]
        for path in paths:
            path.parent.mkdir();path.write_text('OPENROUTER_API_KEY='+path.parent.name+'\n')
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(p.load_api_key(paths)[0],'experiment')
        paths[0].unlink()
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(p.load_api_key(paths)[0],'worktree')

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.DEVNULL)

    def init_git(self):
        self.git('init','-q');self.git('config','user.email','test@example.invalid')
        self.git('config','user.name','test');(self.root/'.gitignore').write_text('.env\n.env.*\n!.env.example\n')
        self.git('add','.gitignore');self.git('commit','-qm','initial')

    def test_ignored_env_passes_and_example_is_allowed(self):
        self.init_git();path=self.root/'.env';path.write_text('OPENROUTER_API_KEY=fixture-credential\n')
        report=p.verify_secret_protection('fixture-credential',str(path),repo=self.root)
        self.assertTrue(report['history_scan_passed'])
        self.assertEqual(self.git('ls-files','.env'),b'')
        self.assertEqual(self.git('check-ignore','.env').strip(),b'.env')
        result=subprocess.run(['git','-C',str(self.root),'check-ignore','.env.example'],capture_output=True)
        self.assertNotEqual(result.returncode,0)

    def test_tracked_dotenv_blocks(self):
        self.init_git();(self.root/'.env').write_text('OPENROUTER_API_KEY=fixture-credential\n')
        self.git('add','-f','.env')
        with self.assertRaises(p.Blocked):
            p.verify_secret_protection('fixture-credential',str(self.root/'.env'),repo=self.root)

    def test_historical_secret_blocks_even_after_deletion(self):
        self.init_git();path=self.root/'accidental.txt';path.write_text('fixture-credential')
        self.git('add','accidental.txt');self.git('commit','-qm','bad history')
        self.git('rm','-q','accidental.txt');self.git('commit','-qm','remove')
        with self.assertRaises(p.Blocked):
            p.verify_secret_protection('fixture-credential','environment',repo=self.root)

    def test_local_snapshot_tree_blocks_without_branch_commit(self):
        self.init_git();path=self.root/'.env';path.write_text('OPENROUTER_API_KEY=fixture-credential')
        self.git('add','-f','.env')
        tree=self.git('write-tree').decode().strip()
        self.git('update-ref','refs/codex/test-snapshot',tree)
        self.git('reset','-q','HEAD','--','.env')
        self.assertEqual(self.git('log','--all','--format=%H','--','.env'),b'')
        with self.assertRaises(p.Blocked):
            p.verify_secret_protection('fixture-credential',str(path),repo=self.root)

    def test_only_explicitly_revoked_blob_may_warn(self):
        self.init_git()
        old='sk-or-v1-'+'a'*64
        path=self.root/'old.txt';path.write_text(old)
        self.git('add','old.txt');self.git('commit','-qm','old credential')
        blob=self.git('rev-parse','HEAD:old.txt').decode().strip()
        self.git('rm','-q','old.txt');self.git('commit','-qm','remove')
        with patch.object(p,'REVOKED_LOCAL_BLOBS',frozenset([blob])):
            report=p.verify_secret_protection('fixture-current','environment',repo=self.root)
            self.assertEqual(report['revoked_local_blob_matches'],1)
            self.assertTrue(report['current_key_absent_from_git'])
            with self.assertRaises(p.Blocked):
                p.verify_secret_protection(old,'environment',repo=self.root)
        with patch.object(p,'REVOKED_LOCAL_BLOBS',frozenset()):
            with self.assertRaises(p.Blocked):
                p.verify_secret_protection('fixture-current','environment',repo=self.root)

if __name__=='__main__':unittest.main()
