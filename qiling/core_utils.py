#!/usr/bin/env python3
# 
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
# Built on top of Unicorn emulator (www.unicorn-engine.org) 

import os, logging, configparser

from keystone import *
from capstone import *
from binascii import unhexlify

from .utils import ql_get_module_function
from .utils import ql_is_valid_arch, ql_is_valid_ostype
from .utils import loadertype_convert_str, ostype_convert_str, arch_convert_str
from .utils import debugger_convert
from .const import QL_OS, QL_OS_ALL, QL_ARCH, QL_ENDIAN, QL_OUTPUT, QL_DEBUGGER
from .const import D_INFO, D_DRPT
from .exception import QlErrorArch, QlErrorOsType, QlErrorOutput


class QlCoreUtils(object):
    def __init__(self):
        super().__init__()

    # normal print out
    def nprint(self, *args, **kw):
        if type(self.console) is bool:
            pass
        else:
            raise QlErrorOutput("[!] console must be True or False")     
        
        # FIXME: this is due to console must be able to update during runtime
        if self.log_file_fd is not None:
            if self.multithread == True and self.os.thread_management is not None and self.os.thread_management.cur_thread is not None:
                fd = self.os.thread_management.cur_thread.log_file_fd
            else:
                fd = self.log_file_fd
            
            args = map(str, args)
            msg = kw.get("sep", " ").join(args)

            if kw.get("end", None) != None:
                msg += kw["end"]

            fd.info(msg)


    # debug print out, always use with verbose level with dprint(D_INFO,"helloworld")
    def dprint(self, level, *args, **kw):
        try:
            self.verbose = int(self.verbose)
        except:
            raise QlErrorOutput("[!] Verbose muse be int")    
        
        if type(self.verbose) != int or self.verbose > 99 or (self.verbose > 1 and self.output not in (QL_OUTPUT.DEBUG, QL_OUTPUT.DUMP)):
            raise QlErrorOutput("[!] Verbose > 1 must use with QL_OUTPUT.DEBUG or else ql.verbose must be 0")

        if self.output == QL_OUTPUT.DUMP:
            self.verbose = 99

        if int(self.verbose) >= level and self.output in (QL_OUTPUT.DEBUG, QL_OUTPUT.DUMP):
            if int(self.verbose) >= D_DRPT:
                try:
                    current_pc = self.reg.arch_pc
                except:
                    current_pc = 0    

                args = (("0x%x:" % current_pc), *args)        
                
            self.nprint(*args, **kw)


    def add_fs_mapper(self, ql_path, real_dest):
        self.os.fs_mapper.add_fs_mapping(ql_path, real_dest)


    # push to stack bottom, and update stack register
    def stack_push(self, data):
        self.arch.stack_push(data)


    # pop from stack bottom, and update stack register
    def stack_pop(self):
        return self.arch.stack_pop()


    # read from stack, at a given offset from stack bottom
    # NOTE: unlike stack_pop(), this does not change stack register
    def stack_read(self, offset):
        return self.arch.stack_read(offset)


    # write to stack, at a given offset from stack bottom
    # NOTE: unlike stack_push(), this does not change stack register
    def stack_write(self, offset, data):
        self.arch.stack_write(offset, data)

    
    # Assembler/Disassembler API

    def create_disassembler(self):
        if self.archtype == QL_ARCH.ARM:  # QL_ARM
            reg_cpsr = self.reg.cpsr
            mode = CS_MODE_ARM
            if self.archendian == QL_ENDIAN.EB:
                reg_cpsr_v = 0b100000
                # reg_cpsr_v = 0b000000
            else:
                reg_cpsr_v = 0b100000

            if reg_cpsr & reg_cpsr_v != 0:
                mode = CS_MODE_THUMB

            if self.archendian == QL_ENDIAN.EB:
                md = Cs(CS_ARCH_ARM, mode)
                # md = Cs(CS_ARCH_ARM, mode + CS_MODE_BIG_ENDIAN)
            else:
                md = Cs(CS_ARCH_ARM, mode)

        elif self.archtype == QL_ARCH.ARM_THUMB:
            md = Cs(CS_ARCH_ARM, CS_MODE_THUMB)

        elif self.archtype == QL_ARCH.X86:  # QL_X86
            md = Cs(CS_ARCH_X86, CS_MODE_32)

        elif self.archtype == QL_ARCH.X8664:  # QL_X86_64
            md = Cs(CS_ARCH_X86, CS_MODE_64)

        elif self.archtype == QL_ARCH.ARM64:  # QL_ARM64
            md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)

        elif self.archtype == QL_ARCH.A8086:  # QL_A8086
            md = Cs(CS_ARCH_X86, CS_MODE_16)

        elif self.archtype == QL_ARCH.MIPS:  # QL_MIPS32
            if self.archendian == QL_ENDIAN.EB:
                md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_BIG_ENDIAN)
            else:
                md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)

        else:
            raise QlErrorArch("[!] Unknown arch defined in utils.py (debug output mode)")

        return md
    
    def create_assembler(self):
        if self.archtype == QL_ARCH.ARM:  # QL_ARM
            reg_cpsr = self.reg.cpsr
            mode = KS_MODE_ARM
            if self.archendian == QL_ENDIAN.EB:
                reg_cpsr_v = 0b100000
                # reg_cpsr_v = 0b000000
            else:
                reg_cpsr_v = 0b100000

            if reg_cpsr & reg_cpsr_v != 0:
                mode = KS_MODE_THUMB

            if self.archendian == QL_ENDIAN.EB:
                ks = Ks(KS_ARCH_ARM, mode)
                # md = Cs(CS_ARCH_ARM, mode + CS_MODE_BIG_ENDIAN)
            else:
                ks = Ks(KS_ARCH_ARM, mode)

        elif self.archtype == QL_ARCH.ARM_THUMB:
            ks = Ks(KS_ARCH_ARM, KS_MODE_THUMB)

        elif self.archtype == QL_ARCH.X86:  # QL_X86
            ks = Ks(KS_ARCH_X86, KS_MODE_32)

        elif self.archtype == QL_ARCH.X8664:  # QL_X86_64
            ks = Ks(KS_ARCH_X86, KS_MODE_64)

        elif self.archtype == QL_ARCH.ARM64:  # QL_ARM64
            ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)

        elif self.archtype == QL_ARCH.A8086:  # QL_A8086
            ks = Ks(KS_ARCH_X86, KS_MODE_16)

        elif self.archtype == QL_ARCH.MIPS:  # QL_MIPS32
            if self.archendian == QL_ENDIAN.EB:
                ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_BIG_ENDIAN)
            else:
                ks = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN)

        else:
            raise QlErrorArch("[!] Unknown arch defined in utils.py (debug output mode)")

        return ks

class QlFileDes:
    def __init__(self, init):
        self.__fds = init

    def __getitem__(self, idx):
        return self.__fds[idx]

    def __setitem__(self, idx, val):
        self.__fds[idx] = val

    def __iter__(self):
        return iter(self.__fds)

    def __repr__(self):
        return repr(self.__fds)
    
    def save(self):
        return self.__fds

    def restore(self, fds):
        self.__fds = fds
