# META
MDSO-Error-Tracking-Analysis



Editing this README
When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thank you to makeareadme.com for this template.

Suggestions for a good README
Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

# Name
Choose a self-explaining name for your project.
META (MDSO-Error-Tracking-Analysis)

# Description
The META tool captures MDSO product errors and if enabled can proactively run scripts to perform tests to gain further feedback.

META_Tool Capabilities
- Products (ServiceMapper, NetworkService, DisconnectMapper and NetworkServiceUpdate)
- Checks for Errors at any time interval set (minutes, hours, days, or weeks)
- Gives a count of each error occurrence.
- Can runs tests on errors of interest that are added to a list.
- Sends information of interest to Webex rooms
- Creates xlsx files containing all errors found.
- Creates a bar graph displaying error counts
- Added API ability to the flask web URL.
- During tests no matter what time interval is set an api request is sent to capture the most up to date logs 
- Current scheduled checks are.
    - Testing every 15 minutes for the “unable to connect to device”.
    - Testing every day for the “Juniper Commit errors”.
    - Every Tues-Fri morning the previous days errors are gathered.self\.date_time_format
    - Every Monday morning the previous week  errors are gathered.

# Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

# Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

Installation
## Setup
Prerequisites:
- python3
- git

1. **Clone the code repo from git into the directory of your choice**

    ``git clone git@gitlab.spectrumflow.net:service-engineering-automation/orchestration/meta.git``

2. **cd into the project's root directory**

    ``cd meta``

3. **Create a virtual environment**

    ``python -m venv venv``

4. **Activate the environment**

    * On Mac/Linux: ``source venv/bin/activate``
    * On Windows: ``source venv/Scripts/activate``

5. **Update pip**

    ``pip install --upgrade pip``

6. **Install the project requirements**

    ``pip install -r requirements.txt``

# Example 1

<img src="www/example_connectivity_checker.png" width="800" height="1025" />

# Example 2

<img src="www/example_daily_error_check.png" width="800" height="771" />

# Support
Michael Smith
michaelx.smith@charter.com

# Team
- Michael Smith
- Robert Saunders
- Christopher Schafer
- Allison Patino
- Alex Arandia
- Kamakshi Guddanti
- Matthew Blacketer
- Donny Newsome

# Project status
to be continued