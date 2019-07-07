# Changelog


## 1.1.0 (2019-07-07)

### New

* Added sections to explain the use of resource and store in tutorial; also added readme jupyter notebook. chg: dev: changed the use of super() in init methods. chg: test: changed tomjerry.py; gauss distribution may return negative time. [Jason Liu]

* Added store facility and some examples, including most simpy examples. [Jason Liu]

* Added a couple simpy examples (carwash, moviegoers). [Jason Liu]

* Changed sched() and process() to allow arbitrary functions; examples and documents have been updated accordingly. [Jason Liu]

* Added regression pytest and tox support. [Jason Liu]


## 1.0.5 (2019-07-04)

### New

* New trappables and conditional waits (1.0.5). new: dev: added support for changelogs generated from git logs. chg: dev: changed resource reserve to acquire. [Jason Liu]

* Redesigned trappables; the processes, events, semaphores, traps, and resources now work with a more intuitive interface design. [Jason Liu]

* Added initial implementation of resource and qstats. [Jason Liu]


## 1.0.4 (2019-07-04)

### New

* Finished trappables and timed waits implementation and accompanying documents (1.0.4). [Jason Liu]

* Updated documents for using trappables and timed wait; and a bug fix. [Jason Liu]

* Added support for conditional wait (wait on multiple trappables and timed wait). [Jason Liu]


## 1.0.1 (2019-07-04)

### New

* Pip ready; simulus has been published on pypi (1.0.1, 1.0.2, 1.0.3). [Jason Liu]


## 0.0.3 (2019-07-04)

### New

* Updated docs and added examples of using trappables; also some minor changes to interface (0.0.3). [Jason Liu]

* Adding trapping mechanisms for inter-process communication. [Jason Liu]


## 0.0.2 (2019-07-04)

### New

* Added some examples using processes for user document. [Jason Liu]

* Added useful functions for direct event scheduling (including resched, cancel, peek, step, and show_calendar). [Jason Liu]

* Added phold example (to test processes). [Jason Liu]

### Changes

* Restructured examples directory (0.0.2). [Jason Liu]

* Minor incremental updates. [Jason Liu]

* Minor updates on a few interface functions including the sleep function. [Jason Liu]

### Fix

* Fixed process scheduling issue. [Jason Liu]


## 0.0.1 (2019-07-04)

### New

* First implementation of simulus, with support of events, processes, semaphores, and simulators; and also the jupyter notebook establishing the simple use cases. [Jason Liu]

* This project got started in the evening on June 14, 2019 with a simple idea of creating an easy-to-use python simulator to replace our somewhat dilapitated Simian simulator and also outdoing the esoteric SimPy simulator. [Jason Liu]

### Changes

* Some minor updates (0.0.1). [Jason Liu]

* Updated the jupyter notebooks. [Jason Liu]

* Updated README.md (mindless update). [Jason Liu]

* Updated README.md. [Jason Liu]


