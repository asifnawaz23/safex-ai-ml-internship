"""
Synthetic dataset generator for DentalSense AI.

Produces a diverse, fully synthetic set of dental-clinic feedback records
spanning several weeks/months and covering every theme and sentiment type.

IMPORTANT: All data is fictional. No real patient information is used.
Run:  python data/generate_dataset.py
"""
import csv
import os

# (feedback_text, iso_date) — hand-authored synthetic reviews grouped by theme/sentiment.
# Dates deliberately span June–September 2026 to exercise trend/volume charts.
RECORDS = [
    # --- Dentist (positive) ---
    ("The dentist explained the procedure very clearly and answered all my questions.", "2026-06-02"),
    ("Dr. Smith was gentle and I felt no pain during the filling.", "2026-06-05"),
    ("The dentist was extremely professional and put me at ease.", "2026-06-11"),
    ("My dentist took the time to walk me through the treatment plan.", "2026-07-01"),
    ("Excellent dentist, very knowledgeable and reassuring.", "2026-07-14"),
    ("The doctor was patient and thorough with my examination.", "2026-08-03"),
    ("Dr. Lee did a wonderful job on my crown, highly recommend.", "2026-08-19"),
    ("The dentist made a nervous patient feel completely comfortable.", "2026-09-04"),
    # --- Dentist (negative) ---
    ("The dentist was rough and did not explain what he was doing.", "2026-06-20"),
    ("I felt rushed by the dentist and my questions were ignored.", "2026-07-22"),
    ("The dentist seemed distracted and made me anxious.", "2026-08-27"),
    ("Very disappointed, the dentist barely spoke to me during the visit.", "2026-09-15"),

    # --- Staff (positive) ---
    ("The receptionist was extremely friendly and welcoming.", "2026-06-03"),
    ("Front desk staff were helpful and sorted my paperwork quickly.", "2026-06-18"),
    ("The hygienist was kind and gave great aftercare advice.", "2026-07-06"),
    ("Reception team was warm and made check-in effortless.", "2026-07-28"),
    ("The nurse was reassuring and very attentive.", "2026-08-09"),
    ("Friendly staff who genuinely seemed to care about patients.", "2026-09-01"),
    # --- Staff (negative) ---
    ("Staff was rude when I asked about the bill.", "2026-06-25"),
    ("The receptionist was dismissive and unhelpful on the phone.", "2026-07-19"),
    ("Front desk staff seemed annoyed by my questions.", "2026-08-14"),
    ("The assistant was impatient and unfriendly.", "2026-09-10"),

    # --- Waiting Time (positive) ---
    ("I was seen right on time, no waiting at all.", "2026-06-07"),
    ("Prompt service, the appointment started exactly on schedule.", "2026-07-11"),
    ("Minimal wait, I was called within five minutes.", "2026-08-05"),
    ("Very efficient, no delays and a quick appointment.", "2026-09-06"),
    # --- Waiting Time (negative) ---
    ("The waiting time was much longer than expected.", "2026-06-09"),
    ("I had to wait 45 minutes past my appointment time.", "2026-06-29"),
    ("Waited almost an hour before being seen, very frustrating.", "2026-07-16"),
    ("The clinic was running late and no one updated us.", "2026-08-21"),
    ("Long delays every time I visit, the scheduling is poor.", "2026-09-12"),
    ("I waited 50 minutes even though I arrived early.", "2026-09-22"),

    # --- Treatment (positive) ---
    ("Very expensive treatment but good quality work.", "2026-06-13"),
    ("The cleaning was thorough and my teeth feel great.", "2026-07-03"),
    ("Painless extraction and excellent follow-up care.", "2026-07-25"),
    ("The filling was done well and feels completely natural.", "2026-08-11"),
    ("My root canal treatment was smooth and pain free.", "2026-09-08"),
    # --- Treatment (negative) ---
    ("The procedure was painful and the numbing wore off too soon.", "2026-06-22"),
    ("My filling fell out a week after the treatment.", "2026-07-30"),
    ("The cleaning felt rushed and my gums were sore afterwards.", "2026-08-24"),
    ("Painful experience during the extraction, would not return.", "2026-09-18"),

    # --- Cleanliness (positive) ---
    ("The clinic was clean and the receptionist was friendly.", "2026-06-04"),
    ("Spotless clinic, everything looked sterile and modern.", "2026-07-08"),
    ("Very hygienic environment, I felt safe throughout.", "2026-08-02"),
    ("The treatment rooms were immaculate and well maintained.", "2026-09-03"),
    # --- Cleanliness (negative) ---
    ("The bathroom was dirty and clearly not cleaned regularly.", "2026-06-27"),
    ("The waiting area looked messy and dusty.", "2026-07-21"),
    ("Instruments were left out and the room felt unhygienic.", "2026-08-29"),

    # --- Pricing (positive) ---
    ("Affordable pricing and they explained the costs upfront.", "2026-06-15"),
    ("Reasonable prices and my insurance was handled smoothly.", "2026-07-12"),
    ("Great value for the quality of care I received.", "2026-08-16"),
    # --- Pricing (negative) ---
    ("The treatment was far too expensive for what it was.", "2026-06-30"),
    ("Hidden charges appeared on my bill that were never mentioned.", "2026-07-24"),
    ("Overpriced and the insurance claim was a hassle.", "2026-08-26"),
    ("The cost was much higher than the original quote.", "2026-09-20"),

    # --- Appointment (positive) ---
    ("Booking an appointment was easy and fast.", "2026-06-06"),
    ("Scheduling online was simple and I got a convenient slot.", "2026-07-09"),
    ("Rescheduling my appointment was quick and hassle free.", "2026-08-07"),
    ("Easy to book and I received a helpful reminder.", "2026-09-05"),
    # --- Appointment (negative) ---
    ("It took three calls to finally book an appointment.", "2026-06-28"),
    ("They cancelled my appointment last minute without notice.", "2026-07-27"),
    ("The booking system is confusing and kept failing.", "2026-08-23"),

    # --- Facilities (positive) ---
    ("The facility is modern and well equipped.", "2026-06-08"),
    ("Comfortable chairs and up to date equipment.", "2026-07-15"),
    ("Great parking and a pleasant, modern waiting room.", "2026-08-13"),
    ("The equipment looked new and the facilities were excellent.", "2026-09-07"),
    # --- Facilities (negative) ---
    ("Parking was impossible and the waiting room was cramped.", "2026-06-24"),
    ("The dental chair was uncomfortable and old.", "2026-07-31"),
    ("The facilities felt outdated and the equipment was noisy.", "2026-08-28"),

    # --- Mixed / ambiguous (exercise Neutral threshold) ---
    ("The visit was okay, nothing particularly stood out.", "2026-06-16"),
    ("It was an average appointment overall.", "2026-07-04"),
    ("Good dentist but the wait was a little long.", "2026-07-18"),
    ("The staff were fine and the treatment was acceptable.", "2026-08-06"),
    ("Not great, not terrible, just a standard checkup.", "2026-08-30"),
    ("The care was decent though the pricing felt a bit high.", "2026-09-11"),
    ("Mixed feelings, friendly staff but a long wait time.", "2026-09-17"),
    ("The appointment happened as scheduled.", "2026-09-25"),

    # --- Short reviews ---
    ("Great service.", "2026-06-10"),
    ("Very professional.", "2026-06-19"),
    ("Terrible experience.", "2026-07-02"),
    ("Highly recommend.", "2026-07-13"),
    ("Would not return.", "2026-07-26"),
    ("Excellent clinic.", "2026-08-01"),
    ("Disappointing visit.", "2026-08-18"),
    ("Friendly and quick.", "2026-09-02"),

    # --- Longer, detailed reviews ---
    ("From the moment I walked in, the receptionist greeted me warmly, the waiting room was spotless, and the dentist explained every step of my treatment in detail before starting. I left feeling well cared for and will definitely be back.", "2026-06-14"),
    ("Although the dentist himself was skilled and the filling was done properly, the overall experience was let down by a 40 minute wait and a bill that was noticeably higher than the quote I was originally given.", "2026-07-20"),
    ("The hygienist was thorough and gentle, taking time to explain how to improve my brushing routine, and the modern equipment made the cleaning quick and comfortable. Excellent value for the price.", "2026-08-15"),
    ("I was extremely nervous about my extraction, but the staff reassured me throughout, the dentist was patient and gentle, and the aftercare instructions were clear and easy to follow. A genuinely positive experience.", "2026-09-09"),
    ("Unfortunately my appointment was cancelled twice, the waiting room was crowded when I finally attended, and the treatment felt rushed. The dentist was polite but the clinic clearly needs better scheduling.", "2026-09-19"),

    # --- Additional varied reviews to pass 100 ---
    ("The dentist was caring and the treatment was painless.", "2026-06-12"),
    ("Reception staff were welcoming and efficient.", "2026-06-17"),
    ("Waited far too long for a simple checkup.", "2026-06-21"),
    ("The clinic was sparkling clean and well organised.", "2026-06-23"),
    ("Pricing was transparent and fair.", "2026-06-26"),
    ("Booking online could not have been easier.", "2026-07-05"),
    ("The parking situation was a nightmare.", "2026-07-07"),
    ("Dr. Patel was fantastic and very gentle.", "2026-07-10"),
    ("The assistant was cold and unhelpful.", "2026-07-17"),
    ("My cleaning appointment was quick and effective.", "2026-07-23"),
    ("The bill was confusing and full of extra fees.", "2026-07-29"),
    ("The new equipment made the visit comfortable.", "2026-08-04"),
    ("Long wait and an unfriendly receptionist.", "2026-08-08"),
    ("The dentist reassured my child throughout the visit.", "2026-08-10"),
    ("Everything was spotless and modern.", "2026-08-12"),
    ("The treatment left me in pain for days.", "2026-08-17"),
    ("Scheduling my follow-up was effortless.", "2026-08-20"),
    ("The facilities were dated but the care was good.", "2026-08-22"),
    ("Rude staff ruined an otherwise fine appointment.", "2026-08-25"),
    ("Affordable and professional dental care.", "2026-08-31"),
    ("The waiting room was calm and comfortable.", "2026-09-13"),
    ("The dentist rushed through my checkup.", "2026-09-14"),
    ("Clean, modern, and friendly clinic overall.", "2026-09-16"),
    ("The extraction was handled with great care.", "2026-09-21"),
    ("Too expensive and the wait was unbearable.", "2026-09-23"),
    ("The hygienist gave excellent, gentle care.", "2026-09-24"),
    ("A smooth, professional, and pleasant visit.", "2026-09-26"),
]


def main():
    out_path = os.path.join(os.path.dirname(__file__), "sample_feedback.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "feedback"])
        for i, (feedback, date) in enumerate(RECORDS, start=1):
            writer.writerow([i, date, feedback])
    print(f"Wrote {len(RECORDS)} synthetic records to {out_path}")


if __name__ == "__main__":
    main()
