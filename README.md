## Dependencies

#### Python 3.6

pip install -r requrements.txt

##### Selenium

wget https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz

sudo sh -c 'tar -x geckodriver -zf geckodriver-v0.26.0-linux64.tar.gz -O > /usr/bin/geckodriver'

sudo chmod +x /usr/bin/geckodriver

rm geckodriver-v0.26.0-linux64.tar.gz

## Run Command

* For multiple thread: gunicorn -w 16 -b localhost:5056 main:app

* For single thread: python main.py run

## Script dependencies after initialization (Directory: ./scripts)

* sh initial_setup_1.sh

* sh initial_setup_2.sh

* sh initial_setup_3.sh
