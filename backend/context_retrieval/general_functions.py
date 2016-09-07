import math


# Adaptation of classic binary search algorithm to search for a string in a given alphabetically sorted list
def binary_search(array, string):

    # Given an array, search string and the upper and lower bounds of aforementioned array search for the string
    def binary_search_execute(search_array, search_string, low, high):

        # Split the array into two equal (or almost equal) parts
        pointer = int(math.floor((low + high) / 2))

        # If the string has been found then return its position
        if search_array[pointer] == search_string:
            return pointer

        # If the array is only one element long and does not contain string then string is not in array
        elif high == low:
            return -1

        # Find out which occurs first alphabetically - the middle element of the array or the search string
        first_alphabetically = min(search_array[pointer], search_string)

        # If the search string occurs first then it must reside in the first half of array (since array is sorted)
        if search_string is first_alphabetically:
            # Recursively call function on first half of array
            return binary_search_execute(search_array, search_string, low, pointer)

        # Otherwise it must reside in second half of array
        else:
            # Recursively call function on second half of array
            return binary_search_execute(search_array, search_string, pointer + 1, high)

    if string is not "":
        # Split into an outer and inner method to reduce number of parameters needed to pass in from other methods
        return binary_search_execute(array, string, 0, len(array) - 1)

    return -1