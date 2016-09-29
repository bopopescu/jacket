#!/usr/bin/python

from retrying import retry

def retry_if_result_is_false(result):
    print result
    return True

def retry_if_exception(result):
    print result
    test = result is False
    print test
    return result is False

def retry_if_connection_err(exception):
    print exception
    return False

@retry(stop_max_attempt_number=3,
       wait_fixed=1000,
        retry_on_result=retry_if_result_is_false,
       retry_on_exception=lambda exc: True)
def test():
    print "test"
    raise Exception("xxxxxxxxxxxxx")

def main():
    test()


if __name__ == "__main__":
    main()