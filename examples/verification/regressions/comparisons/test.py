#!/usr/bin/env python3
"""Exhaustive small-domain tests of bundled-data comparison mapping in Xcelium."""
from pathlib import Path
import os
import subprocess
import tempfile

source=Path(__file__).resolve().parent
output=Path(os.environ.get('BALSA_COMPARE_TEST_DIR',tempfile.mkdtemp(prefix='balsa-comparisons-'))).resolve()
home=Path(subprocess.check_output(['balsa-config','-d'],text=True).strip())
cases=[('unsigned8x8',8,8,False),('unsigned4x8',4,8,False),('unsigned8x4',8,4,False),
       ('signed8x8',8,8,True),('signed4x8',4,8,True)]
for name,aw,bw,signed in cases:
    work=output/name; work.mkdir(parents=True,exist_ok=True)
    sign=' signed' if signed else ''
    text=(source/'compare8.balsa').read_text().replace('a : Byte; b : Byte',
        'a : {}{} bits; b : {}{} bits'.format(aw,sign,bw,sign))
    (work/'compare8.balsa').write_text(text)
    commands=[['balsa-c','-b','compare8.balsa'],
              ['balsa-netlist','--simulation-initialise','-X','example/four_b_rb','-n','verilog','compare8.breeze'],
              [os.environ.get('XRUN','xrun'),'-64bit','-sv','-top','compare_tb',
               '+define+balsa_simulate','+define+balsa_init_time=20',
               '+define+AW='+str(aw),'+define+BW='+str(bw),
               str(home/'share/tech/example/example-cells.v'),'compare8.v',str(source/'compare_tb.sv')]+
              (['+SIGNED'] if signed else [])]
    for index,args in enumerate(commands):
        log=work/('stage-'+str(index)+'.log')
        with log.open('w') as stream:
            result=subprocess.run(args,cwd=str(work),stdout=stream,stderr=subprocess.STDOUT,timeout=180)
        if result.returncode:
            raise SystemExit('FAIL: '+name+'; see '+str(log)+'\n'+log.read_text()[-2000:])
    final=log.read_text()
    marker='PASS: {} input pairs; all four relational operators'.format(1<<(aw+bw))
    assert marker in final and 'FAIL:' not in final, str(log)
    print(name+': '+marker,flush=True)
print('PASS: 143360 input pairs / 573440 relational results; artifacts: '+str(output))
