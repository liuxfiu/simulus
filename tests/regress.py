#
# Regression Test
#
# We run all the examples in the examples/basics directory and compare
# their output with that from the previous run.  Note that the
# test_basic_examples() method will be picked up to run by pytest.
#

import glob, os, sys, difflib

class bcolors:
    OK = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def diff(s1, s2):
    s1=s1.splitlines(1)
    s2=s2.splitlines(1)
    diff=difflib.unified_diff(s1, s2)
    return ''.join(diff)
    
def test_basic_examples():
    failed = 0
    script_file = os.path.realpath(__file__)
    script_path = os.path.dirname(script_file)
    basics_files = os.path.realpath(os.path.join(script_path, '..', 'examples', 'basics', '*.py'))
    simpy_files = os.path.realpath(os.path.join(script_path, '..', 'examples', 'simpy', '*.py'))
    pyfs = glob.glob(basics_files)+glob.glob(simpy_files)
    outfs = ['.out'.join(f.rsplit('.py', 1)) for f in pyfs]
    for pyf, outf in zip(pyfs, outfs):
        cmd = 'python '+pyf
        try: 
            s1 = os.popen(cmd).read()
        except:
            raise(bcolors.FAIL+"ERROR: can't run "+pyf+bcolors.ENDC)

        with open(outf, "r") as f:
            s2 = f.read()

        if s1 == s2:
            print(bcolors.OK+"good: "+pyf+bcolors.ENDC)
        else:
            print(bcolors.FAIL+"bad: "+pyf+bcolors.ENDC)
            print(diff(s1,s2))
            failed += 1
    assert failed == 0
            
if __name__ == '__main__':
    test_basic_examples()
