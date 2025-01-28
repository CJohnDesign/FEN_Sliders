-- Create Scripts table
CREATE TABLE scripts (
    script_id VARCHAR(10) PRIMARY KEY,
    presentation_id VARCHAR(10) REFERENCES presentations(presentation_id) ON DELETE CASCADE,
    script_array JSON NOT NULL
);

-- Insert FEN_MF1 script
INSERT INTO scripts (script_id, presentation_id, script_array)
VALUES (
    'FEN_MF1_S1',
    'FEN_MF1',
    '[
    "Now that we''ve reviewed what the Medfirst Wellness Plan, let''s go ahead and cover the Med First Plan 1 offered by MedFirst.",
    "As mentioned before, any time we''re seeing the numbers listed next to a benefit, it indicates required verbiage at the bottom of the page that must be covered with the client. The plan benefits are listed on the left and the benefit details on the right.",
    "Starting with our Primary Care Office Visit, we can see it will cover 3 visits per calendar year at a $25 Co payment with the maximum of $150. They must access providers through First Health Network when utilizing the Physician Services to be covered by the plan.",
    "For the Specialist or Urgent Care Office Visit, we can see it will cover 1 visit per calendar year at a $50 Co payment with the maximum of $300. They must access providers through First Health Network when utilizing the Physician Services to be covered by the plan. Also all sickness benefits are subject to a 30-day waiting period before benefits are payable under the plan.",
    "Next up is the In-Patient Hospitalization Benefit. This is an Indemnity Benefit and would receive $1000 per day for a maximum of $5,000 per Calendar year. This benefit will not pay out for pre-existing conditions for the first 12 months of coverage.",
    "The telemedicine benefit offered by Kindly Human through Recurral Health, there is a $0.00 consult fee and no maximum visit amount. This is a benefit that allows members to keep healthcare cost down when it comes to certain physician services. Recuro Health would be the telemedicine number they would call provided on their member ID Card.",
    "Next up is the RX benefit. This is offered through Best Choice RX and for this particular plan members would utilize the Best Choice RX Group discount program. It is important to point out that this is a group discount program NOT a prescription drug plan and is available at participating pharmacies only.",
    "This means it will offer discounts for medications, but they will not have predictable Copayments like the other prescription drug coverage we are about to review. It is extremely important to explain this benefit accurately to clients.",
    "For Healthcare Ninja, this benefit is a great tool to utilize to keep healthcare costs down and would be utilized with the Indemnity Benefits like Hospitalization as well as other physician service benefits once the plan benefits have been exhausted.",
    "As we continue, you''ll notice the required verbiage at the bottom of the page that correlates to specific benefits and benefit details that we must cover with our members.",
    "Continuing on for the minimal essential coverage preventative health services summary of benefits. We want to make sure when covering these with clients that we''re going over all verbiage. Preventative benefit would be the same for all MedFirst Plans.",
    "Now when reviewing the preventative health services, you''ll notice we have our benefits, our intervals and our requirements.",
    "Our requirement field not only lets us know what requirements are needed from clients for the services, but also in some instances explains what the benefit is and who it may be applicable to.",
    "Benefit explains the preventative service being provided.",
    "Interval explains how often they are able to utilize the benefits.",
    "Our requirement field not only lets us know what requirements are needed from clients for the services, but also in some instances explains what the benefit is and who it may be applicable to.",
    "For example for the domino aortic aneurysm screenings benefit. It lets me know that this is by ultrasonography in men, they can only use it once per lifetime, and they must be of ages 65 to 75 years who''ve ever smoked. So this would NOT be for non-smokers and or people aged 64 or younger or 76 and older.",
    "As you guys can see, the list is extensive, but it is a list of preventative services.",
    "Next would be immunizations. It is important to keep in mind what immunizations are available for which age group so it''s key to check the age group prior to quoting a benefit being covered.",
    "So as you can see, birth through 6 year olds would be the eligibility group for these vaccinations",
    "As we continue children from 7 through 18 years old and we also have adults 19 years or older.",
    "These immunizations are based upon CDC recommendations and it''s important as well to make sure that we''re covering the exclusions with our clients.",
    "Some additional items to keep in mind whenever reviewing the MedFirst 1 Plan.",
    "Members must access providers through First Health Network when utilizing the Physician Services to be covered by the plan.",
    "It is important to point out that Best Choice RX Group discount program is a group discount program NOT a prescription drug plan and is available at participating pharmacies ONLY.",
    "The telemedicine benefit offered by Kindly Human through Recurral Health, allows members to keep healthcare costs down when it comes to certain physician services and there is no maximum to this benefit.",
    "Healthcare Ninja, this benefit is a great tool to utilize to keep healthcare costs down and would be utilized with the Indemnity Benefits like Hospitalization as well as other physician service benefits once the plan benefits have been exhausted.",
    "Most importantly, remember to care for your clients in a complete and compliant manner. Thank you for participating in First Enroll''s Training and continue to be great!"
]'
); 