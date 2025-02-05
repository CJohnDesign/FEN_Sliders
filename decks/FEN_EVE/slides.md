---
id: FEN_{{deck_key}}
theme: ../../
title: | 
  {{ Plan Name }}
info: |
  ## {{ Plan Name }} Review
  A look at the {{ Plan Name }} benefits and details.
verticalCenter: true
layout: intro
themeConfig:
  logoHeader: ./img/logos/FEN_logo.svg
  audioEnabled: true
transition: fade-out
drawings:
  persist: false
---

<SlideAudio deckKey="FEN_{{deck_key}}" />

# {{ Plan Name }} Review

Understanding the details and benefits of the **{{ Plan Full Name }}**

---
transition: fade-out
layout: default
---

## {{ Plan Name }} Overview

<v-clicks>

- {{ Overview Point 1 }} through **{{ Organization }}**
- **{{ Benefit Category 1 }}** for various situations
- **{{ Benefit Category 2 }}** and support tools
- **{{ Benefit Category 3 }}** through {{ Feature }}
- **{{ Benefit Category 4 }}** support

</v-clicks>

---
transition: fade-out
layout: default
---

## Key Features and Benefits

<v-clicks>

**{{ Benefit Type 1 }}**

**{{ Benefit Type 2 }}**

**{{ Benefit Type 3 }}**

**{{ Benefit Type 4 }}** (varies by plan)
</v-clicks>

<v-click>

**{{ Additional Benefit }}** through {{ Partner }}
<div class="grid grid-cols-1 gap-4 items-center px-8 py-4">
  <img src="" class="h-12 mix-blend-multiply" alt="{{ Brand }} Logo">
</div>

</v-click>

---
transition: fade-out
layout: default
---

## Cost Management Tools

<v-click>

**{{ Tool Name }}** ({{ Acronym }})
</v-click>

<v-click>

**{{ Feature 1 }}** System
</v-click>

<v-click>

**{{ Feature 2 }}** Support
</v-click>

---
transition: fade-out
layout: default
---

## How {{ Tool Name }} Works

<v-clicks>

1. Enroll through **{{ Organization }}**
2. {{ Step 2 }}
3. {{ Step 3 }}
4. Receive {{ Document }} **({{ Acronym }})**
5. {{ Step 5 }}
6. **{{ Final Outcome }}**

</v-clicks>

---
transition: fade-out
layout: default
---

## Preventive Care and Wellness

<v-clicks>

- **{{ Service 1 }}** Services
- **{{ Service 2 }}** Programs
- **{{ Partner }}** provides {{ service_type }}

</v-clicks>

---
transition: fade-out
layout: default
---

## Telehealth Services

<v-clicks>

- **{{ Feature 1 }}**
- **{{ Feature 2 }}**
- **{{ Feature 3 }}** available
- **{{ Feature 4 }}** to care

</v-clicks>

---
transition: fade-out
layout: default
---

## Advocacy and Support Services

<v-clicks>

- **{{ Service Style }}** healthcare advocacy
- **{{ Service 1 }}** assistance
- **{{ Service 2 }}** options
- **{{ Service 3 }}** support

</v-clicks>

---
transition: fade-out
layout: one-half-img
image: img/pages/{{plan_brochure_image_1}}.jpg
---

## {{ Plan 1 Name }} (1/2)

<v-click>

**{{ Benefit Category 1 }}**
- {{ Detail 1 }}
- {{ Detail 2 }}
- {{ Detail 3 }}
- {{ Detail 4 }}
<Arrow v-bind="{{ x1:480, y1:160, x2:560, y2:160, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

<v-click>

**{{ Benefit Category 2 }}**
- {{ Detail 1 }}
- {{ Detail 2 }}
<Arrow v-bind="{{ x1:480, y1:215, x2:560, y2:215, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

<v-click>

**{{ Benefit Category 3 }}**
- {{ Detail 1 }}
- {{ Detail 2 }}
- {{ Detail 3 }}
<Arrow v-bind="{{ x1:480, y1:340, x2:560, y2:340, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

---
transition: fade-out
layout: one-half-img
image: img/pages/{{plan_brochure_image_1}}.jpg
---

## {{ Plan 1 Name }} (2/2)

<v-click>

**{{ Benefit Category 4 }}**
- {{ Detail 1 }}
- {{ Detail 2 }}
<Arrow v-bind="{{ x1:480, y1:370, x2:560, y2:370, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

<v-click>

**{{ Benefit Category 5 }}**
- {{ Detail 1 }}
- {{ Detail 2 }}
<Arrow v-bind="{{ x1:480, y1:410, x2:560, y2:410, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

<!-- Insert as many plans as needed. Make sure they are always returned as a two part section -->

---
transition: fade-out
layout: default
---

## Comparing the Plans

| **Feature** | **{{ Plan 1 }}** | **{{ Plan 2 }}** | **{{ Plan 3 }}** |
|---------|----------|----------|-----------|
| {{ Feature 1 }} | {{ Value 1.1 }} | {{ Value 1.2 }} | {{ Value 1.3 }} |
| {{ Feature 2 }} | {{ Value 2.1 }} | {{ Value 2.2 }} | {{ Value 2.3 }} |
| {{ Feature 3 }} | {{ Value 3.1 }} | {{ Value 3.2 }} | {{ Value 3.3 }} |
| {{ Feature 4 }} | {{ Value 4.1 }} | {{ Value 4.2 }} | {{ Value 4.3 }} |
| {{ Feature 5 }} | {{ Value 5.1 }} | {{ Value 5.2 }} | {{ Value 5.3 }} |

---
transition: fade-out
layout: one-half-img
image: img/pages/{{plan_brochure_image_final}}.jpg
---

## Definitions and Limitations

<v-click>

**{{ Category 1 }}**
- {{ Limitation 1 }}
- {{ Limitation 2 }}
- {{ Limitation 3 }}
<Arrow v-bind="{{ x1:480, y1:160, x2:550, y2:160, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

<v-click>

**{{ Category 2 }}**
- {{ Limitation 1 }}
- {{ Limitation 2 }}
<Arrow v-bind="{{ x1:480, y1:255, x2:550, y2:255, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

<v-click>

**{{ Category 3 }}**
- {{ Limitation 1 }}
- {{ Limitation 2 }}
<Arrow v-bind="{{ x1:480, y1:360, x2:550, y2:360, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

<v-click>

**{{ Category 4 }}**
- {{ Limitation 1 }}
- {{ Limitation 2 }}
- {{ Limitation 3 }}
<Arrow v-bind="{{ x1:480, y1:420, x2:550, y2:420, color: 'var(--slidev-theme-accent)' }}" />
</v-click>

---
transition: fade-out
layout: default
---

## Key Takeaways and Reminders

<v-clicks>

- **{{ Feature 1 }}** benefits
- **{{ Feature 2 }}** included
- **{{ Feature 3 }}** benefits
- **{{ Requirement }}** required

</v-clicks>

---
transition: fade-out
layout: end
line: Thank you for participating in the {{ Plan Name }} Review. Continue to be great!
---

# Thank You!

Continue to be great!

<img src="./img/logos/FEN_logo.svg" class="h-12 mt-32" alt="FirstEnroll Logo">

