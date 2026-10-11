"""Retained original-instruction helper, sanitized to use the public pinned image.

Dummy memory and recorded stubs have no electrical/peripheral behavior.
"""
from unicorn import Uc,UcError,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_PROT_READ,UC_PROT_EXEC,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from config import get_configuration
ROM=get_configuration().rom
def u32(x):return x&0xffffffff
def s32(x):return (x+2**31)%2**32-2**31
def s16(x):return (x+2**15)%2**16-2**15
def div(a,b):return abs(a)//abs(b)*(1 if (a<0)==(b<0) else -1)
class Machine:
 def __init__(self,stubs=None):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);self.u.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M0)
  self.u.mem_map(0,0x20000);self.u.mem_write(0x5000,ROM);self.u.mem_protect(0,0x20000,UC_PROT_READ|UC_PROT_EXEC)
  self.u.mem_map(0x20000000,0x4000);self.u.mem_write(0x20000000,ROM[0x49d4:]);self.stubs=stubs or {};self.calls=[];self.accesses=[]
  self.u.hook_add(UC_HOOK_CODE,self.code)
 def code(self,u,a,size,_):
  if a in self.stubs:
   self.calls.append({'address':hex(a),'args':[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]})
   result=self.stubs[a](self) if callable(self.stubs[a]) else self.stubs[a]
   if result is not None:u.reg_write(UC_ARM_REG_R0,u32(result))
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def set(self,a,v,width=4):self.u.mem_write(a,int(v&((1<<(width*8))-1)).to_bytes(width,'little'))
 def get(self,a,width=4,signed=False):return int.from_bytes(self.u.mem_read(a,width),'little',signed=signed)
 def run(self,a,*args):
  for r in range(UC_ARM_REG_R0,UC_ARM_REG_R12+1):self.u.reg_write(r,0)
  for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(r,u32(v))
  self.u.reg_write(UC_ARM_REG_SP,0x20003e00);self.u.reg_write(UC_ARM_REG_LR,0x1001)
  self.u.emu_start(a|1,0x1000,count=100000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x1000,hex(self.u.reg_read(UC_ARM_REG_PC))
  return s32(self.u.reg_read(UC_ARM_REG_R0))
