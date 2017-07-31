import requests
import copy
import smtplib
import email_template
import hashlib
from apscheduler.schedulers.blocking import BlockingScheduler
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# TODO - DOESNT CHECK ALL RESULTS ON CL, ONLY FIRST 100
# TODO - ADD PICTURE IN EMAIL


def open_page(url):
    html = requests.get(url, verify=False).text
    # filter / split up result string into HTML Segments
    result_array = html[html.find('<ul class="rows">'):].split('<li class="result-row"')
    clean_listings = []
    # each entry begins with <li class="result-row" ... ends with </li>
    # properties from the HTML we want :
    # 1. Title DONE
    # 2. Price DONE
    # 3. Link to listing DONE

    for listing in result_array:
        attributes = []
        # For each listing, parse out the 3 important properties
        # 2 step approach, 1st find start of field, 2nd find end of field
        # This is because we don't know length / size of the field

        title = listing[listing.find('class="result-title hdrlnk">') + 28:]
        title = title[:title.find('</a>')]
        attributes.append(title)

        price = listing[listing.find('class="result-price">') + 22:]
        price = price[:price.find('</span>')]
        attributes.append(price)

        link = listing[listing.find('<a href="') + 9:]
        link = link[:link.find('"')]
        attributes.append(link)

        clean_listings.append(attributes)
    # End of listing loop
    clean_listings.remove(clean_listings[0])  # remove first result (empty result)
    return clean_listings


def search_listings(listings, max_price):
    good_listings = []
    for listing in listings:
        listing_lowercase = copy.copy(listing)  # We want to preserve case of original listing
        listing_lowercase[0] = listing_lowercase[0].lower()  # shift listing to lowercase for searching

        bad_words = ['want', 'buy', 'looking', 'cd', 'video', 'theater', '7', '7.1', '5.1-channel', '5.1' 'digital',
                     'surround', 'recorder', 'console', 'record', 'boom', 'disc', 'dvd', 'repair', 'parts', 'mp3', 'car']

        good_words = ['pioneer', 'sansui', 'onkyo', 'fisher', 'marantz', 'realistic', 'harman', 'klipsch', 'bose', 'sony',
                      'sherwood', 'bang', 'kenwood', 'olufsen', 'altec', 'jbl', 'mcintosh', 'zenith', 'wharfedale',
                      'rotel', 'boston acoustics', 'teac', 'luxman', 'project one']

        # Choosing to eliminate those BS results with a price of $1
        # Results to be searched must be under set max price
        if int(listing[1]) != 1 and int(listing[1]) < max_price:
            # print(listing_lowercase)
            # print('good result' + repr(listing[1]))
            # Search filter time
            # if listing[0] contains 'good result' keep. - Here's the keywords ex Pioneer, Vintage, ect.
            # elif listing[0] contains ... skip (bad keywords ex. Looking, Want) (buy side)
            # else skip - no meat
            # Order:
            # 1) check for hit
            # 2) Check for false positive

            # print('found ' + listing[0] + ' $' + listing[1])
            if any(word in listing_lowercase[0] for word in good_words):  # hit
                #print('found ' + listing_lowercase[0] + ' $' + listing_lowercase[1])
                # FIRST FILTER WORKS. MUST BE FAILING IN SECOND FILTER
                if not any(word in listing_lowercase[0] for word in bad_words):  # eliminate false positives
                    print('found ' + listing_lowercase[0] + ' $' + listing_lowercase[1])
                    good_listings.append(listing)  # add listing to master list
    # returns array of checked valid listings
    return good_listings


def do_job(url_to_search, max_price):
    print('I will print this every hour.')
    listings = open_page(url_to_search)
    search_listings(listings, max_price)


def send_emails(listings):
    s = smtplib.SMTP(host='smtp.office365.com', port=587)
    s.starttls()
    s.login('wesolow7@uwm.edu', '')

    msg = MIMEMultipart()  # create a message

    # add in the actual person name to the message template
    message = email_template.make_email(listings)

    # Prints out the message body for our sake
    # print(message)

    # setup the parameters of the message
    msg['From'] = 'wesolow7@uwm.edu'
    msg['To'] = 'mmettej@gmail.com'
    msg['Subject'] = "New Vintage Audio Listings on Craigslist"

    # add in the message body
    msg.attach(MIMEText(message, 'html'))

    # send the message via the server set up earlier.
    s.send_message(msg)
    del msg

    # Terminate the SMTP session and close the connection
    s.quit()

def check_if_sent(results):
    # First, check if the listings have been sent or not and filter them.
    old_hashes = []
    new_listings = []

    old_lines = open('sent_listings.txt', 'r')
    for line in old_lines:
        old_hashes.append(line.strip('\n'))  # create list to search

    for listing in results:
        # listing_hash = hashlib.md5(listing[2]).hexdigest()  # hashes link to the CL listing ADD THIS .encode('utf-8')
        if not hashlib.md5(repr(listing)).hexdigest() in old_hashes:
            new_listings.append(listing)

    for listing in new_listings:
        print 'new listings! ' + 'found ' + listing[0] + ' $' + listing[1]
    return new_listings


def mark_sent(listings):
    # Append to the listings to a text file containing other previously sent listings.
    with open('sent_listings.txt', 'a') as text_file:
        for listing in listings:
            # text_file.write(listing[2] + '\n')  # plain text of the link
            text_file.write(hashlib.md5(repr(listing)).hexdigest() + '\n')  # writes hash of listing to text file
        # NOW all of the listings that have been sent are written to the file as an md5 hash
    print('marked')

def main():
    MAX_PRICE = 120
    URL_TO_SEARCH = 'https://milwaukee.craigslist.org/search/sss?' \
                    'query=stero+%7C+stereo+%7C+reciever+%7C+receiver' \
                    '&sort=rel&min_price=2&max_price=' + repr(MAX_PRICE)

    print('Starting bot...')
    scheduler = BlockingScheduler()
    # scheduler.add_job(do_job(URL_TO_SEARCH, MAX_PRICE), 'interval', hours=1)
    # scheduler.start() # run. Hangs up the program while running

    # \/ For testing \/
    listings = open_page(URL_TO_SEARCH)  # step 1
    results = search_listings(listings, MAX_PRICE)  # step 2
    print'---------------------------------------------------------------'
    new_listings = check_if_sent(results)
    # send_emails(new_listings)  # literally sends an email step 3
    print 'SENDING EMAIL (not really)'
    mark_sent(new_listings)  # step 4

main()
