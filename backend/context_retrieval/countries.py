
# Read in text file containing list of countries sorted by continent
countries_file = file('backend/context_retrieval/countries.txt', 'r')
countries = countries_file.readlines()

for i, country in enumerate(countries):
    countries[i] = country.strip()


# TODO: Create method to determine if country is found in database (don't create matrix if its not)
# Find the continent in which a country resides
def find_continent(country_index):

    # The ranges in which the continent's respective countries lie in the text file
    # E.g. the first 47 countries belong to the European continent
    continents = [['Europe', range(1, 48)], ['Africa', range(48, 102)], ['South America', range(102, 115)],
                  ['North America', range(115, 142)], ['Asia', range(142, 191)], ['Oceania', range(191, 204)],
                  ['Antarctica', range(204, 206)]]

    # Look through continents and check which one the country belongs to
    for index, continent in enumerate(continents):
        if country_index in continent[1]:
            return index

    # If it is not in the range then return not found
    # This is sometimes returned in error as some countries may not exist in the text file due to name changes etc.
    return 7


def get_country_index(search_country):

    search_country = str(search_country).strip()

    # Loop through the countries and look for the inputted country (can't use binary search as it is unsorted)
    for index, current_country in enumerate(countries):

        # Remove whitespace and check if text file country matched inputted country
        if search_country == current_country:
            return index

    return -1
