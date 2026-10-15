"""Omit one legacy-only counter update from release; retain VD period sampling."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def apply(work):
 work=Path(work).resolve();assert work.is_relative_to(ROOT/'artifacts/private')
 p=work/'src/emount.c';s=p.read_text();old='\t\t\tem_frame_period_n++;';assert s.count(old)==1
 p.write_text(s.replace(old,'#ifndef EA9_NO_LOG\n'+old+'\n#endif'))
