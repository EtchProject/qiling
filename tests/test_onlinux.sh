#!/bin/bash

# 
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

python3 ./test_posix.py && 
python3 ./test_elf_multithread.py &&
python3 ./test_elf_ko.py &&
python3 ./test_android.py && 
python3 ./test_debugger.py && 
python3 ./test_uefi.py && 
python3 ./test_shellcode.py && 
python3 ./test_edl.py &&
python3 ./test_qnx.py &&
pwd
ls ../qiling/engine
cd ../qiling/engine/tests && python3 ./test_evm.py 