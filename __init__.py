import requests

def open_page(url_name):
    html = requests.get(url_name, verify=False).text
    start_index = html.find('<ul class="rows">')
    result = html[start_index:]
    print result


def main():
    print('Starting bot...')
    open_page('https://milwaukee.craigslist.org/search/sss?query=stereo&sort=rel&max_price=100')

main()