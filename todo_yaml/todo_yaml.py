def get_body(docs):
    if len(docs) == 0:
        return {}
    else:
        return docs[0]

def get_footer(docs):
    if len(docs) > 1:
        return docs[1]
    else:
        return {}


def prepare_query(s):
    return f'.. | select(type == "object" and ({s}))'