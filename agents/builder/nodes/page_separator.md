 OK, so this project so far has taken a PDF, broken it all into individual pages, summarize the pages, made sure it got all of the data from the tables using a GPT-4o call, Then we generate a single presentation in the aggregate summaries noted. Based on that we create a first version of the slides and a first version of the audio script and they are saved separately. The purpose of the page separator is to break everything up, using some simple regex To build a state object with an array of objects. Each object has two key value pairs, one being the Page slide and another being the Page script. For context, my definition of a page is just this, a page is made up of a slide and a script. 
 
 here is an example of three slides - notice how the header of each slide has --- above and below it. there can me any number of lines between the ---. This indicates the content of the slide below it. In the first object I want to store the slide header and slide content of the page.
     ```
     ---
id: FEN_TDK
theme: ../../
title: | 
  Transforming Data Through Knowledge
info: |
  ## Transforming Data Through Knowledge Review
  A look at the Transforming Data Through Knowledge benefits and details.
verticalCenter: true
layout: intro
themeConfig:
  logoHeader: ./img/logos/FEN_logo.svg
  audioEnabled: true
transition: fade-out
drawings:
  persist: false
---

<SlideAudio deckKey="FEN_TDK" />

# TDK Plan Overview

Understanding the details and benefits of the **Transforming Data Through Knowledge** plan.

---
transition: fade-out
layout: default
---

## Plan Overview

<v-clicks>

- Provided by **America's Choice Health Care**
- Administration by **Detego Health**
- **Accessibility** for Individuals and Families
- **Emphasizes** Personal impact
- **Ensures** Vital services within reach

</v-clicks>

---
transition: fade-out
layout: default
---

## Core Plan Elements

<v-click>

**Coverage**

- Physician Services and Hospitalization
- Virtual Visits and Prescriptions
- Wellness and Advocacy Services
- Tailored Healthcare options

</v-click>

<v-click>

**Plan Structure**

- Tiered plan options
- Specific Co-pays per service
- Visit Allowances
- Maximum coverage limits

</v-click>

<v-click>

**Eligibility**

- Individual and family coverage
- Emphasis on affordability 
- Access to health services
- Flexible coverage options

</v-click>
```



Here is Example of the script output. Notice how it uses the --- but in a different way. it looks like this: `--- Cover ---``
```
---- Cover ----

Hello, everyone! Thank you for joining today's session on the TDK, the Transforming Data Through Knowledge plan. We'll walk through this plan's unique features and benefits, designed to provide accessible healthcare solutions. Let's dive right in!

---- Plan Overview ----

The Transforming Data Through Knowledge plan

is brought to you by America's Choice Health Care, 

with Administration by Detego Health. 

This plan is all about accessibility, ensuring that individuals and families who may not qualify for traditional medical plans can still access vital healthcare services. 

It's designed to have a personal impact, making sure necessary care is within reach.

Moving forward, let's explore the core elements of the plan.

---- Core Plan Elements ----

This plan offers coverage options tailored to a variety of healthcare needs. 

These include Physician Services, Hospitalization, Virtual Visits, Prescriptions, Wellness, and Advocacy Services. 

Each plan tier has specific co-pays, visit allowances, and maximum coverage limits, ensuring flexibility. 

Eligibility is focused on individuals and families who value affordability and health services.

Now, let's look into the common service features.
```



 so these two examples would represent three pages and they should be safe together in a J which is then saved to state.
 
 
 
 
 ------
 
 
 once we have this beautiful Jayson object with the contents of each page, 
 
 again, a page is made up of a slide and a script, which have a header and a content.

Example of a page:
- page:
  - slide:
    - header:
    - content:
  - script:
    - header:
    - content:

Now the validator is going to loop through these pages and compare the content of the slide and the script to the content of the page in the Json object. If they match, the page is valid. If they don't match, the page is invalid. If the page comes back is not valid, then we should continue the current process of giving each example to the script and slide rider, respectively, and return that to state to recheck again. While we're at it, we should probably keep track of the changes in state too, so make sure to iterate that with two digits appended to the end of the state key.

I want to create a very logical pattern for this recursive agent. We should load the prompts up with a lot of context. 

We can give the task of writing it to the script, writer and slides writer note but I wanna create an additional prompt while we're in the validation step, which should be stored in the prompts directory. It should vary intelligently build the context to logically explain how things should sync. If I'm the first attempt to rewrite it, it still comes back false, we should be putting the previous step into the prompt as well with the new instructions so that it can hold context of the changes it's making. (I have a question about this because I'm worried that we might be getting redundant and expanding the contact links too much, will this be going into the same thread by default?)