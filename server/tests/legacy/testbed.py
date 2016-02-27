from providers.google_rss import GoogleRSS


url_list = ['https://lh4.googleusercontent.com/-s2WOC8Z-cu8/UtVS1nj0FfI/AAAAAAAACPs/RIhCZxCLuB4/w1200-h812-p/2013%2BLondon%2Bmeeting%2B098-sRGB%2Bsmall.jpg',
            'https://lh4.googleusercontent.com/-s2WOC8Z-cu8/UtVS1nj0FfI/AAAAAAAACPs/RIhCZxCLuB4/w1200-h812/2013%2BLondon%2Bmeeting%2B098-sRGB%2Bsmall.jpg',
            'https://lh4.googleusercontent.com/-s2WOC8Z-cu8/UtVS1nj0FfI/AAAAAAAACPs/RIhCZxCLuB4/w1200-h812-d/2013%2BLondon%2Bmeeting%2B098-sRGB%2Bsmall.jpg',
            'https://lh4.googleusercontent.com/-s2WOC8Z-cu8/UtVS1nj0FfI/AAAAAAAACPs/RIhCZxCLuB4/s0/2013%2BLondon%2Bmeeting%2B098-sRGB%2Bsmall.jpg',
            'https://lh4.googleusercontent.com/-s2WOC8Z-cu8/UtVS1nj0FfI/AAAAAAAACPs/RIhCZxCLuB4/s0-d/2013%2BLondon%2Bmeeting%2B098-sRGB%2Bsmall.jpg',
            'https://lh4.googleusercontent.com/-s2WOC8Z-cu8/UtVS1nj0FfI/AAAAAAAACPs/RIhCZxCLuB4/2013%2BLondon%2Bmeeting%2B098-sRGB%2Bsmall.jpg',
            'https://lh4.googleusercontent.com/-YaAT5PPovF8/UuoXyUqgV2I/AAAAAAABbC0/-MzlbFRFAek/w506-h750/20140128_153852.jpg',
            'https://lh4.googleusercontent.com/-YaAT5PPovF8/UuoXyUqgV2I/AAAAAAABbC0/-MzlbFRFAek/s0-d/20140128_153852.jpg']

for url in url_list:
    print(GoogleRSS.parse_full_image_url(url))