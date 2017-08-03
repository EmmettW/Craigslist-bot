import requests
import copy
import smtplib
import email_template
import hashlib
import image_scraper
from apscheduler.schedulers.blocking import BlockingScheduler
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# TODO - ADD PICTURE IN EMAIL


def get_all_listings(url, num_pages):
    listings = []
    url_argv = 0  # listing number displayed. Increments by 120 on CL
    for x in range(0, num_pages):
        # Gather listings for how many pages specified.
        tmp_url = url
        if not url_argv == 0:
            tmp_url += repr(url_argv)
        listings.extend(open_page(tmp_url))
        url_argv += 120
    return listings


def open_page(url):
    html = requests.get(url).text  # verify=False (for testing w/ connection issues)
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

        bad_words = ['want', 'buy', 'looking', 'cd', 'video', 'theater', '7.1', '5.1-channel', '5.1' 'digital', 'car',
                     'surround', 'recorder', 'console', 'record', 'boom', 'disc', 'dvd', 'repair', 'parts', 'mp3',
                     'headphone', 'iso', '6.1', 'cassette', 'vcr', 'new', 'manual', 'bookshelf', 'av', 'din', 'remote',
                     'hdtv', 'a/v', 'track', 'tape', 'guitar', 'sub', 'subs', 'auto']

        good_words = ['pioneer', 'sansui', 'onkyo', 'fisher', 'marantz', 'realistic', 'harman', 'klipsch', 'bose',
                      'sherwood', 'bang', 'kenwood', 'olufsen', 'altec', 'jbl', 'mcintosh', 'zenith', 'wharfedale',
                      'rotel', 'boston acoustics', 'teac', 'luxman', 'project one', 'jvc', 'sony', 'phase linear',
                     'technics']

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
            if any(word in listing_lowercase[0] for word in good_words):  # hit
                if not any(word in listing_lowercase[0] for word in bad_words):  # eliminate false positives
                    good_listings.append(listing)  # add listing to master list
                    # print(listing[0] + '  $' + listing[1])
    return good_listings  # returns array of checked valid listings


def check_if_sent(results):
    # First, check if the listings have been sent or not and filter them.
    old_hashes = []
    new_listings = []
    old_lines = open('sent_listings.txt', 'r')

    for line in old_lines:
        old_hashes.append(line.strip('\n'))  # create list to search
    for listing in results:
        if not hashlib.md5(repr(listing).encode('utf-8')).hexdigest() in old_hashes:
            print('Found!! ' + listing[0] + ' $' + listing[1])
            new_listings.append(listing)
    return new_listings


def authenticate():
    # ONLY asks for pass. I don't feel like typing the email address in every time.
    # I also don't feel comfortable keeping my pw in plain text on my disk
    # AlSO don't feel like implementing AES or RSA encryption just to do the password for now.
    logged_in = False
    login_data = []

    with open('user_info.txt', 'r') as text_file: # There is a text file containing hash to check
        e_address = text_file.readline()
        valid_hash = text_file.readline()

    while not logged_in:
        pw = raw_input('Enter password for email server : ')
        hashed_pw = hashlib.sha256(pw.encode('utf-8')).hexdigest()
        if hashed_pw == valid_hash:
            print(e_address + "Successfully logged in.")
            logged_in = not logged_in # Now we are successfully logged in.
            login_data.append(e_address)
            login_data.append(pw)
        else:
            print ('Login failure please try again.\n')
    return login_data


def send_email(listings, login_data):
    if listings:
        address = login_data[0]
        pw = login_data[1]
        s = smtplib.SMTP(host='smtp.office365.com', port=587)
        s.starttls()
        s.login(address, pw)

        msg = MIMEMultipart()  # create a message

        # add in the actual person name to the message template
        message = email_template.build_email(listings)

        # Prints out the message body for our sake
        # print(message)
        # setup the parameters of the message
        msg['From'] = address
        msg['To'] = 'mmettej@gmail.com'
        msg['Subject'] = "New Vintage Audio Listings on Craigslist"

        # add in the message body
        msg.attach(MIMEText(message, 'html'))
        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg
        # Terminate the SMTP session and close the connection
        s.quit()
        print('New listings have been sent.')
    else:
        print('No email to send')


def mark_sent(listings):
    # Append to the listings to a text file containing other previously sent listings.
    with open('sent_listings.txt', 'a') as text_file:
        for listing in listings:
            # writes hash of listing to text file
            text_file.write(hashlib.md5(repr(listing).encode('utf-8')).hexdigest() + '\n')
        # NOW all of the listings that have been sent are written to the file as an md5 hash
    print('marked')


def create_job(url_to_search, max_price):
    print('I will print this every hour.')
    listings = open_page(url_to_search)
    search_listings(listings, max_price)


def scrape_thumbnails(url):
    # Not working. image_scraper
    print('grabbing images')
    # TODO - change the path
    print(
    image_scraper.scrape_images(url, no_to_download=20, download_path='C:\IntellJ\dl4j-examples', dump_urls=True))


def main():
    scheduler = BlockingScheduler()
    MAX_PRICE = 100
    URL_TO_SEARCH = 'https://milwaukee.craigslist.org/search/sss?' \
                    'query=stero+%7C+stereo+%7C+reciever+%7C+receiver+%7C+amp+%7C+hifi' \
                    '&sort=date&min_price=2&max_price=' + repr(MAX_PRICE) + '&s='
    print('Starting bot...')

    # scheduler.add_job(create_job(URL_TO_SEARCH, MAX_PRICE), 'interval', hours=1)
    # scheduler.start() # run. Hangs up the program while running

    #    \/ For testing \/
    listings = get_all_listings(URL_TO_SEARCH, 3)  # step 1
    results = search_listings(listings, MAX_PRICE)  # step 2
    print('---------------------------------------------------------------')
    new_listings = check_if_sent(results)
    send_email(new_listings)  # literally sends an email step 3
    print('SENDING EMAIL')
    mark_sent(new_listings)  # step 4
    #scrape_thumbnails('https://www.google.com')

main()
