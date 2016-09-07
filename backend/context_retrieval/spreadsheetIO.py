def matrix_to_spreadsheet(tag_array, matrix, spreadsheet_file):

    # Save all tags as a string to print on first row of each spreadsheet
    tags = "," + (", ".join(tag_array)) + "\n"

    new_file = ""

    for tag_index, tag in enumerate(tag_array):

        # Print all tags in first column
        new_file += tag.encode('unicode-escape') + ","

        # Print occurrences related to aforementioned tag
        for other_tag_index, occurrence in enumerate(tag_array):
            new_file += str(matrix[tag_index, other_tag_index]) + ","

        # Move to the next line
        new_file += "\n"

    ssheet_file = open(spreadsheet_file, 'w')
    ssheet_file.write(tags + new_file)


def save_results(results, spreadsheet_file):

    new_file = ""

    for result in results:
        for field in result:
            new_file += str(field)
            new_file += ','
        new_file += '\n'

    ssheet_file = open(spreadsheet_file, 'w')
    ssheet_file.write(new_file)