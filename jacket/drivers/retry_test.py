#!/usr/bin/python

from retrying import retry


def retry_if_result_is_false(ret):
    return True

@retry(stop_max_attempt_number=3,
       wait_fixed=2000,
       retry_on_result=retry_if_result_is_false,
       retry_on_exception=lambda exc: True,
       )
def test():
    print "test"
    raise Exception("xxxxxxx")

def main():
    try:
        test()
    except Exception:
        print "++++++++++++++++++++"

if __name__ == '__main__':
    main()
