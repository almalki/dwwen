from bs4 import BeautifulSoup
import markdown2

__author__ = 'abdulaziz'


def markdown2text(mdtext):
    html = markdown2.markdown(mdtext)
    text = BeautifulSoup(html).get_text()
    return text


def summary(text, length=300, suffix='...'):
    if len(text) <= length:
        return text
    else:
        return ' '.join(text[:length+1].split(' ')[0:-1]) + suffix
