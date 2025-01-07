"""This is the doc string for the file1 file where we can say things about the python module.add()
We can write long text if we want.

* topic 1
* topic 2    

"""


def file1_func1():
    """This function does nothing."""
    pass


def file1_func2(param1: int, param2: int):
    """
    This function returns the sum of the values you pass in as arguments.

    :param param1: Integer to sum.
    :type param1: int
    :param param2: Integer to sum.
    :type param2: int
    :return: Sum of the given parameter's values.
    :rtype: int

    """
    return param1 + param2


def file1_func3():
    """This function does nothing."""
    pass


def file1_func4(param1: str, param2: int, param3: bool):
    """
    This function returns the 10 or the param2 times 3 if ...

    :param param1: String to check if we should do something.
    :type param1: string
    :param param2: Base value to the multiplication.
    :type param2: int
    :param param3: If we should do the multiplication or not.
    :type param3: bool
    :return: Multiplication result or 10.
    :rtype: int
    
    """
    if param3 and param1 == "Y":
        return param2 * 3
    return 10


def file1_func5(param1: str, param2: int):
    """
    This function returns true.

    :param param1: Some String...
    :type param1: string
    :param param2: Some Integer...
    :type param2: int
    :return: Always true.
    :rtype: bool

    """

    print(param1, param2)
    return True