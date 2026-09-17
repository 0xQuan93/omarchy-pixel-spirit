#!/usr/bin/env python3
"""Measure local planning with isolated discovery and hard effect/model guards."""
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'plugin'))
import brain
import command_bank

def main():
    timings={}
    with tempfile.TemporaryDirectory() as tmp, patch.object(brain,'BASE',Path(tmp)), \
         patch.object(command_bank,'discover',return_value=({}, {}, {})), \
         patch('shutil.which',return_value='/fixture/tool'), \
         patch.object(brain,'execute',side_effect=AssertionError('Unexpected effect')), \
         patch('inference.request',side_effect=AssertionError('Unexpected model call')):
        for message in ('just open my clipboard','open browser and terminal','open files and set volume to 35%'):
            samples=[]
            for _ in range(25):
                start=time.perf_counter();reply=brain.chat(message);samples.append((time.perf_counter()-start)*1000)
                assert reply['route']=='local' and reply['action']
            timings[message]={'medianMs':round(statistics.median(samples),2),'p95Ms':round(sorted(samples)[23],2)}
        samples=[]
        for _ in range(25):
            draft=brain.chat('open browser and terminal')
            start=time.perf_counter();reply=brain.chat('skip the browser',pending_plan=draft['action']);samples.append((time.perf_counter()-start)*1000)
            assert len(reply['steps'])==1
        timings['skip the browser (pending plan)']={'medianMs':round(statistics.median(samples),2),'p95Ms':round(sorted(samples)[23],2)}
    print(json.dumps({'samplesPerCase':25,'modelCalls':0,'executedActions':0,'discovery':'isolated empty fixture','timings':timings},indent=2))
if __name__=='__main__':main()
