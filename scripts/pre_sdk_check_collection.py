"""Collect independent pre-SDK failures; a failed check always rejects the gate."""
import json,time,traceback
from pathlib import Path


class CheckCollection:
    def __init__(self, failure_report=None):
        self.results=[]
        self.failures=[]
        self.failure_report=Path(failure_report) if failure_report else None

    def run(self,name,check,*,fallback=None):
        started=time.monotonic()
        try:
            value=check()
        except (Exception,SystemExit) as error:
            record={'name':str(name),'status':'failed','seconds':round(time.monotonic()-started,3),
                    'exception':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
            self.results.append(record);self.failures.append(record)
            print('FAILED PRE-SDK: '+str(name)+'\n'+record['traceback'],flush=True)
            if self.failure_report:
                self.failure_report.parent.mkdir(parents=True,exist_ok=True)
                self.failure_report.write_text(json.dumps({'status':'failed','checks':self.results,'failed_checks':self.failures},ensure_ascii=False,indent=2)+'\n')
            return fallback if fallback is not None else {'status':'failed','check':str(name),'exception':str(error)}
        self.results.append({'name':str(name),'status':'passed','seconds':round(time.monotonic()-started,3)})
        return value

    def require_success(self):
        if self.failures:
            raise SystemExit('PRE-SDK FAILED: '+', '.join(item['name'] for item in self.failures))
