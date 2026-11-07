#!/usr/bin/env python3
"""Build and test the bank offline; optional saved-loader/ARM tests require Unicorn."""
from datetime import datetime
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'artifacts/private'/('profile-bank-tests-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(exist_ok=False)
    build=folder/'build'
    subprocess.run([sys.executable,str(ROOT/'scripts/build-profile-bank.py'),'--output',str(build)],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/test-profile-bank.py'),'--build',str(build),
                    '--output',str(folder/'portable')],check=True)
    print('Public-source build and portable tests passed. Optional compiled-ARM and private-loader checks are documented separately.')


if __name__=='__main__': main()
