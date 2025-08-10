import faker
import json
import os

remove_list = [
    "EncodedTitle",
    "ClickURL",
    "externalJobs",
    "Photo",
    "Content",
    "internalProjects",
    "Recomendations",
    "ActivityLinks",
    "Username",
]
name_list = ["Title", "FirstName", "LastName"]
works_list = ["Owner"]
contact_list = ["Email", "Phone", "Mobile"]
id_list = ["Id"]
works_id_list = ["ExpertId"]


def remove_data(processed_record):
    for attribute in remove_list:
        if attribute in processed_record:
            del processed_record[attribute]


def anonymize_name(processed_record, list, name, last_name, full_name):
    for attribute in list:
        if attribute in processed_record:
            if "FirstName" in attribute:
                processed_record[attribute] = processed_record[attribute].replace(
                    processed_record[attribute], name
                )
            elif "LastName" in attribute:
                processed_record[attribute] = processed_record[attribute].replace(
                    processed_record[attribute], last_name
                )
            else:
                processed_record[attribute] = processed_record[attribute].replace(
                    processed_record[attribute], full_name
                )


def anonymize_contacts(processed_record, email, phone, mobile):
    for attribute in contact_list:
        if attribute in processed_record:
            if "Email" in attribute:
                processed_record[attribute] = processed_record[attribute].replace(
                    processed_record[attribute], email
                )
            elif "Phone" in attribute:
                processed_record[attribute] = processed_record[attribute].replace(
                    processed_record[attribute], phone
                )
            elif "Mobile" in attribute:
                processed_record[attribute] = processed_record[attribute].replace(
                    processed_record[attribute], mobile
                )

def anonymize_id(processed_record, list, fake_id):
    for attribute in list:
        if attribute in processed_record:
                if "Id" in attribute:
                    processed_record[attribute] = fake_id
                elif "ExpertId" in attribute:
                    processed_record[attribute] = fake_id


def anonymize_data():
    """Anonymize the data by replacing personal information with fake data."""
    print("Anonymizing data...")

    fake = faker.Faker()
    original_file = os.path.join("data", "original_data.json")
    expert_file = os.path.join("data", "experts.json")

    data = json.load(open(original_file))
    expert_data = json.load(open(expert_file))
    for expert_record in expert_data:
        original_expert_id = expert_record["Id"]
        fake_id = fake.unique.random_int(min=111111, max=999999)
        fake_name = fake.first_name()
        fake_last_name = fake.last_name()
        fake_full_name = f"{fake_name} {fake_last_name}"
        fake_email = f"{fake_name.lower()}.{fake_last_name.lower()}@roche.com"
        fake_phone = fake.phone_number()
        fake_mobile = fake.phone_number()
        remove_data(expert_record)
        for record in data:
            if original_expert_id == record["ExpertId"]:
                remove_data(record)
                anonymize_name(
                    record, works_list, fake_name, fake_last_name, fake_full_name
                )
                anonymize_contacts(record, fake_email, fake_phone, fake_mobile)
                anonymize_id(record, works_id_list, fake_id)
        anonymize_name(
            expert_record, name_list, fake_name, fake_last_name, fake_full_name
        )
        anonymize_contacts(expert_record, fake_email, fake_phone, fake_mobile)
        anonymize_id(expert_record, id_list, fake_id)

    works_cleaned_json_object = json.dumps(data, indent=4)
    experts_cleaned_json_object = json.dumps(expert_data, indent=4)
    with open(os.path.join("data", "works_cleaned.json"), "w") as outfile:
        outfile.write(works_cleaned_json_object)
    with open(os.path.join("data", "experts_cleaned.json"), "w") as outfile:
        outfile.write(experts_cleaned_json_object)
