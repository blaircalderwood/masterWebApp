from datetime import datetime
import json
import pymysql
import location
import flickr_data.flickr_api as fa


epoch_day = 86400
epoch_year = epoch_day * 365

conn = None
cur = None


# Return the time of day
# Morning is 0, afternoon 1, evening 2, night 3 and unknown 4
def time_of_day(time):

    if time is None:
        return 4

    # One record in the dataset crashes the program with an unknown error so catch this
    try:

        # Return a datetime version of inputted string
        def to_time(string):
            return datetime.strptime(string, '%I:%M%p').time()

        try:
            # Get the time from the datetime object
            time = datetime.time(time)

        # Sometimes the Flickr API returns a date that is in a slightly different format
        except TypeError:
            return 4

        # Determine time of day
        if to_time('6:00AM') <= time <= to_time('11:59AM'):
            return 0
        elif to_time('12:00PM') <= time <= to_time('5:59PM'):
            return 1

        elif to_time('6:00PM') <= time <= to_time('11:59PM'):
            return 2
        else:
            return 3

    # Sometimes the Flickr API returns a date that is in a slightly different format
    except AttributeError:
        return 4


# Inspired by http://stackoverflow.com/questions/16139306/determine-season-given-timestamp-in-python-using-datetime
# Get the season in which the inputted date lies
# Spring is 0, summer 1, autumn 2 and winter 3
def time_of_year(date):

    try:
        date = to_date(date)

        # The numbers in the range are the first and last days of the year in which this season occurs
        # E.g. spring occurs from day 79 to day 171 (range is non-inclusive on upper limit) of each year
        seasons = [range(79, 172), range(172, 265), range(265, 356)]

        # Convert date to day number
        day_of_year = date.timetuple().tm_yday

        # If day of year lies in range then it is in that season
        for index, season in enumerate(seasons):
            if day_of_year in season:
                return index

    # Sometimes the Flickr API returns a date that is in a slightly different format
    except AttributeError:
        pass

    # Otherwise it is winter
    return 3


# Return if it was a weekday/weekend when given a date
# Monday to Thursday is weekday (0) and Friday to Sunday is weekend (0)
def day_of_week(date):

    try:
        if to_date(date).weekday() <= 4:
            return 0
    # Sometimes the Flickr API returns a date that is in a slightly different format
    except AttributeError:
        pass

    return 1


def to_date(date):

    # If a string has been passed in then convert it to datetime
    if isinstance(date, basestring):
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')

    return date


def collect_date_tags():

    start_of_2013 = 1356998400
    end_of_2013 = 1388534400

    tags = []

    open_connection()

    for date in range(start_of_2013, end_of_2013, epoch_day):

        # Get tags for this date in 2013, 2014 and 2015 respectively
        write_tags(date, fa.get_tags_date(date))
        write_tags(date, fa.get_tags_date(date + epoch_year))
        write_tags(date, fa.get_tags_date(date + (epoch_year * 2)))

    close_connection()

    return tags


def write_tags(date, tags):

    date = datetime.fromtimestamp(date).timetuple().tm_yday
    tags = json.dumps(tags)
    cur.execute("REPLACE INTO dates (day_of_year, tags) VALUES(%s, %s)", (date, tags))
    conn.commit()


def open_connection():

    global conn
    global cur

    # Connect to the mysql server
    conn = pymysql.connect(host='localhost', port=3306, user='root', passwd='password', db=location.db)

    # Set the connection timeout to be very high as the database may need to be open for a long time
    conn.query('SET GLOBAL connect_timeout=28800')
    cur = conn.cursor()


def close_connection():

    global conn
    global cur
    cur.close()
    cur = None
    conn.close()
    conn = None
