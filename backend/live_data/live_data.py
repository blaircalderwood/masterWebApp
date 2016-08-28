import eventful

api = eventful.API('smL46RmRwBM5BJ98')

trigger_file = open("live_data/triggers.txt")
triggers = trigger_file.read()
triggers = triggers.split("\n")


def check_triggers(tags):

    for index, tag in enumerate(tags):

        for trigger in triggers:
            if trigger in tag:
                return index

    return -1


def get_data(time):

    events = api.call('/events/search', q='music', l='Glasgow', t=time)
    for event in events['events']['event']:
        # print event
        print "%s at %s on %s" % (event['title'], event['venue_name'], event['start_time'])