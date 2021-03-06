[![Build Status](https://travis-ci.org/carolynjoneslee/vamonos.svg)](https://travis-ci.org/carolynjoneslee/vamonos)

*¡Vámonos!*
===========
Learn more about the developer: www.linkedin.com/in/carolynjoneslee/

*¡Vámonos!* is a fullstack web application designed for planning an itinerary of events for groups of people travelling together. Integration of the Eventbrite API allows users to browse events happening across the globe, or find activities happening at their destination, during their travel dates. Users can add their friends, and automatically keep track of who wants to attend each event. *¡Vámonos!* uses Google Maps to dynamically display the location of each event, and the Twilio SMS API to send out text message reminders before the trip begins! Lastly, the app automatically generates a PDF version of the itinerary, containing information for each day about the events planned, and who is attending each event.

![Homepage](https://raw.githubusercontent.com/carolynjoneslee/vamonos/master/static/img/screenshot-tripplanner.png)
![EventDetails](https://raw.githubusercontent.com/carolynjoneslee/vamonos/master/static/img/screenshot-eventdetails.png)

#### Technologies
Python, Flask, SQLite3, SQLAlchemy,
HTML/CSS, Twitter Bootstrap,
Javascript, jQuery, jQuery UI, Moment.js, AJAX,
Eventbrite API, Google Maps API, Twilio API

#### Version 2.0

###### Custom Notifications
I'd like to allow users to customize notification options, such that individualized text messages are sent out before certain events begin, or when trip details change, etc.

###### Google Calendar
In a future version, I'd want to integrate the Google Calendars API such that users could export the events from their itinerary directly to a Google Calendar, or import events from a Google Calendar onto their itinerary.    

###### Facebook Friends
I would like to incorporate the Facebook API, allowing users to login/signup through Facebook, and include their Facebook friends in their travel plans.
