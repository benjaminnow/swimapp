# Swimapp

This is a website which is made specifically for my swim team. It keeps track of attendance mainly. This solved the problem of having many coaches using paper versions of attendance and then having to combine it all in one place. This process of getting all the attendance sheets from the different coaches takes my coach at least an hour a day. He manually enters the data from paper into excel. This tool allows all the coaches to keep track of attendance digitally and use the tool all at the same time.

## Features

* attendance tracking for swimmers
* add/delete swimmers
* add jobs(jobs that need to get done before/after practice by swimmers)
* job choosing algorithm - it is a weighting system that takes into account the difficulty of jobs the person has done as well as the amount
* set attendance for the day - the total attendance a swimmer could get if they showed up to the whole practice
* archival tool - exports data from mysql database into google sheets of coach
* attendance graph for each swimmer
* motivation quote adder for coach

## Getting Started

To get this project up and running on localhost:
1. clone it or download the zip file to your computer
2. Run the requirements.txt file with pip
3. get the schema.sql file and run it to make a new database
4. CD into the project directory
5. run "python app.py"

## Screenshots/Gifs

## Deployment

I deployed this on a Digital Ocean Ubuntu VPS. This website has infrequent usage to I went with the $5 tier. This website uses nginx and gunicorn as a webserver. I use FileZilla as a FTP client to transfer the files from my machine to the server. Once on the webserver, install the requirements.txt and setup mysql. Then run the schema.sql file to get the db set up. Then navigate into the directory on the webserver where the project is stored and type "gunicorn app:app".

## Built With

* [Flask](http://flask.pocoo.org/) - The web framework used
* [MySQL](https://www.mysql.com/) - Database used
* [PyMySQL](https://github.com/PyMySQL/PyMySQL) - Python MySQL client
* [bootstrap-table](http://bootstrap-table.wenzhixin.net.cn/) - an extension of bootstrap tables
* [wtforms](https://github.com/wtforms/wtforms) - Python forms library
* [chartkick](https://www.chartkick.com/) - Used to make the graphs
* [google-api-python-client](https://developers.google.com/api-client-library/python/) - API used to interact with Google Sheets
* [passlib](https://passlib.readthedocs.io/en/stable/) - password encryption
* [gunicorn](http://gunicorn.org/) - web server
* [nginx](https://www.nginx.com/resources/wiki/) - proxy server
* [Let’s Encrypt](https://letsencrypt.org/) - certificates
* [Digital Ocean](https://www.digitalocean.com) - hosting

## Contributing

This application should be pretty much done once it is on GitHub. If you have any changes you want to make just contact me.


## Authors

* **Ben Campbell** - *Lead Developer*

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Thanks to these youtubers for helping me get started with Flask: [Traversy Media](https://www.youtube.com/user/TechGuyWeb), [Pretty Printed](https://www.youtube.com/channel/UC-QDfvrRIDB6F0bIO4I4HkQ) and [Google Developers](https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw)
* Thanks to Digital Ocean for providing great hosting tutorials!

## How the "job choosing" algorithm works

The job choosing algorithm was made because I think that everyone should be equally contributing to the team.

1. The function ```get_min``` gets the minimum amount of people needed from going through all of the jobs and adding up the minimums
2. The function ```get_available``` gets the available people(people who are at practice and will be entered into the "here" table in the db)
3. The function ```get_job_total``` gets the job total for each person and adds them all together. This forms the range of the random number generation.
4. The function ```high_low``` adds ```high``` and ```low``` keys to the dictionary taken from the "here" table which has each swimmer ```job_total``` and ```id```
5. Each swimmers' high and low values define their range. Their range is as big as their job total. People with higher job totals will have bigger ranges, a higher chance of being picked, and a higher chance of doing harder jobs.
6. The main purpose of the ```choose_people``` function is to choose people and then sort them into their jobs based on their job totals. People with a higher job total will go into harder jobs. Once those spots are filled, it will continue filling people into jobs with the harder ones being filled up first all the way down to the easiest jobs with people with the lowest job totals.
7. The ```choose_people``` function takes the dictionary created from the ```high_low``` function and turns it into a list so it can be modified.
8. The variable ```total = get_job_total()``` gets the whole range and ```count = get_min()``` gets the minimum people needed to complete all the jobs. If this minimum is not met, job choosing will not happen.
9. Then there is a loop which chooses random numbers in the range. It is ```random.randint(1, total)``` instead of ```random.randint(0, total)``` because the range doesn't use start at 0. This is because a person is chosen if the random number if ```num > low``` and ```num <= high```. This shows that the low value will not lead to a pick.
10. If the random number is within the range, it will add that swimmers' id and job total to the list ```idList```.
11. After their information has been added to the list it will subtract their job total from the overall total. This reduces the range.
12. The chosen swimmers' info will then be popped out of the ```rangeList```.
13. ```break``` is used because the person is already found and the loop doesn't need to be find more than one person.
14. Then the second for loop is run which runs the ```high_low``` function's logic to create new high and low values for each swimmer.
15. After the main loop finishes so that there are as many people chosen as required, ```idList``` is sorted based on job totals in descending order. This serves the function of giving the people who have the highest totals the hardest jobs.
16. Then a database connection is made to the jobs table and selects the job which has the dump attribute set to 1. This means that all the people who are not in the chosen list will get put into the "dump" job
17. The loop goes through the people chosen and checks for matches out of all the swimmers. If there is a match ```found = True``` and they are not entered into the database. If there is not the opposite happens.
18. The function then returns the chosen list of swimmers to be assigned to the other jobs.
19. The ```choose_jobs``` function is to select the swimmers for jobs.
20. It first checks if the minimum people required is greater than the number of people attending practice that day. If it is, then job choosing will not happen.
21. Then a database connection is made to get the data from the jobs table. It extracts the id, minimum, and difficulty level of each job. Then that list is sorted based on difficulty level in descending order.
22. Then the loop puts people into the hardest jobs first. ```start``` and ```jobMinimum``` variables are used in the range because it defines how many people to choose for a job.
23. Then the chosen people are inserted into the database. The job history table keeps the entries indefinitely while the jobs_done table is just used for the front end.

## How I Created This

I came up with this idea because I wanted to learn about web development and I wanted to do something that could solve a real world problem. This was going to be my project for the Summer of 2017.

# Week one

* I did my research on which web framework to use - eventually decided on Flask because of it's simplicity, documentation, and community.
* I did the basic Flaskr project on the flask website to get something up and running
* I then moved onto another project which would have all of the features I would want(CRUD)
* Found [Traversy Media tutorial](https://www.youtube.com/watch?v=zRwy8gtgJ1A&list=PLillGF-RfqbbbPz6GSEM9hLQObuQjNoj_) on a basic flask project which inspired this project
* I finished those tutorials and moved onto planning my project

# Week two

* Took the bare layout of the project from the tutorial and started to modify it to my needs
* I kept the login code
* I modified the add article code into add swimmer code
* I gave each swimmer a page(work in progress) to later display their attendance history
* I added a training group attribute in the db so that swimmers now needed a name and a training group to be created
* On the dashboard, the swimmers can now be viewed by training group instead of all at once

# Week three

* added user registration
* I added an attendance table to the database
* On the dashboard, the coach is now able to add custom amounts of attendance(ex: 120%, 80%, 50%)
* On the individual swimmer page, there is a portion where the swimmers can view their attendance history with the date and amount
* added a decorator to check if the person logged in was an admin. If they were they could get access to certain pages and if not, they were redirected to a login screen.

# Week four

* Added "here" page - When a coach adds attendance for a swimmer ```attending = 1``` in the swimmers table. If they are attending, they are added to the "here" table. This will be used later for the job choosing algorithm since only people who are at practice should be available.
* Added button and logic to remove people from the "here" list once practice is over
* Added way to make jobs - duties that need to be done at the end of practice by swimmers
* Started to make the job choosing algorithm - most of it worked but it was a flawed and would be fixed weeks later when I finally realized it

# Week five

* Worked more on the job choosing algorithm
* I added field "dump" in the adding jobs form - this would put all of the excess people who were at practice into this job
* I added a feature to penalize people who left practice early - they would have points against them which would make them more likely in the future to be chosen for hard jobs
* Added ability to remove jobs if that job no longer needed to be done
* I added a new page which showed who had been chosen for jobs
* I made the person's cell turn green from white in the dashboard table if attendance had been added to them - showed to the coach that they were at practice
* I added the ability to take points away from a person for doing extra work - this would make them less likely to be picked for hard jobs

# Week six

* Added more privilege checks(admin, logged in)
* Made a swimmer search feature using ```LIKE``` in MySQL - later would remove this and just search client side
* Made the "set attendance" page and functionality - this would allow coaches to set the highest achievable attendance for the day and would serve as the denominator in the percent calculation
* Started to host this project on a live web server

# Week seven

* Worked more on the job choosing algorithm - I realized that people would be chosen more than once. This was because it was choosing random numbers but they could be chosen more than once. I needed unique random numbers. I fixed this problem later this week.
* Removed swimmer search because there were better methods
* I started to research easier ways to search the swimmers
* I found a library called bootstrap-table which would be able to search for swimmers and give options to sort by column
* I implemented bootstrap-table library into all my tables
* Added a way to undo a delete if a swimmer got deleted by accident

# Week eight

* I added a decorator to check for super admin(my head coach) - only he should be able to access certain parts of the site
* Added an archival/reset page - this would allow him to export data eventually to Google Sheets and to reset totals for the next season
* I had to do many days of research on how to used Google's api-client-library. There were not many resources so I tinkered around until I got something working.
* Learned the basics of Oauth and tokens
* I switched over from using flask-mysql to PyMySQL
* I added the archival of weekly attendance, end season attendance
* I made the reset buttons for job total, individual attendance total, group attendance totals, and weekly attendance history
* I added the weekly attendance graphs for each swimmer - my coach would export weekly attendance to google sheets every week so I saved these values and they were used for the graphs.
* I added a check in the registration form if the username was already registered

# Week nine

* Made the program slightly more modular by taking the db config out of app.py and into its own file
* Made a forms.py file for the form classes
* Made the first commit of this project onto github
* I added access codes so that only people from my swim team are able to register - when the coach creates a swimmer, a nine digit access code is created. He can then print these all out for the swimmers. Then the swimmers can each register themselves if they want to view the website at home.
* On the archive page I made the functionality to export the access codes to google sheets for my coach to print out
* I added the ability to add different training groups instead of being hard coded in
* I added a motivational quote creator - my head coach is able to login and change the quote which is displayed on the home page
* Made a requirements.txt file, License file, and a readme to go along with my github project

# Week ten
