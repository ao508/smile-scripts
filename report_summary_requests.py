# Request:
# - request ID
# - project ID
# - isCmoRequest value

# Request samples:
# - How many in original request?
# - How many that are missing fields required for label generation?
# - How many that are missing other key fields that Voyager needs?

import sys
import os
import csv
import json

REQUEST_SUMMARY_REPORT = {}

REQUEST_SUMMARY_REPORT_KEYS = ["REQUEST_ID", "LOGGED_REQUEST_STATUS", "PROJECT_ID", "IS_CMO_REQUEST", "TOTAL_NUM_SAMPLES", "FAILED_NUM_SAMPLES", "DETAILED_SAMPLE_ERRORS"]

LABEL_GEN_FIELD_PTID = ["cmoPatientId", "normalizedPatientId"]
LABEL_GEN_FIELD_SAMPLETYPE = ["specimenType", "sampleOrigin", "cmoSampleClass"]
LABEL_GEN_FIELD_NUCACID = ["sampleType"]

OTHER_ESSENTIAL_SAMPLE_FIELDS = ["investigatorSampleId", "baitSet"]

# detailed sample report format: sample_id: LABEL_GEN_MISSING_FIELDS=[fields missing for label generation], OTHER_ESSENTIAL_MISSING_FIELDS=[other essential fields];
# sample can have the required fields for label generation but might be missing other fields that were identified as essential for downstream operations (i.e., voyager needs baitSet and/or recipe)

def extract_request_details(json_data):
	request_id = json_data['requestId']
	project_id = json_data['projectId']
	is_cmo_request = json_data['isCmoRequest']

	samples = json_data['samples']
	total_samples = len(json_data['samples'])

	sample_details = []
	for s in samples:
		# check patient id fields
		label_gen_fields_missing = []
		has_pt_id_fields = False
		if "cmoPatientId" in s.keys() and s["cmoPatientId"] != "":
			has_pt_id_fields = True
		elif "cmoSampleIdFields" in s.keys() and "normalizedPatientId" in s["cmoSampleIdFields"].keys():
			has_pt_id_fields = True
		else:
			label_gen_fields_missing.extend(["cmoPatientId", "normalizedPatientId"])

		# has at least one sample type abbreviation field
		has_sample_abbrev_fields = False
		for f in LABEL_GEN_FIELD_SAMPLETYPE:
			if f in s.keys() and s[f] not in ["", "null"]:
				has_sample_abbrev_fields = True
				break
		if not has_sample_abbrev_fields:
			label_gen_fields_missing.extend(LABEL_GEN_FIELD_SAMPLETYPE[:])

		has_nuc_acid_abbrev_fields = False
		if "cmoSampleIdFields" in s.keys():
			cmoSampleIdFields = s["cmoSampleIdFields"]
			if "sampleType" in cmoSampleIdFields.keys():
				if cmoSampleIdFields["sampleType"] != "" or (cmoSampleIdFields["naToExtract"] != "" or (s["baitSet"] != "")):
					has_nuc_acid_abbrev_fields = True
		if not has_nuc_acid_abbrev_fields:
			label_gen_fields_missing.extend(["sampleType", "naToExtract", "baitSet"])

		other_missing = []
		for f in OTHER_ESSENTIAL_SAMPLE_FIELDS:
			if not f in s.keys():
				other_missing.append(f)

		if len(label_gen_fields_missing) > 0 or len(other_missing) > 0:
			sample_map = {'LABEL_GEN_MISSING_FIELDS':label_gen_fields_missing, 'OTHER_ESSENTIAL_MISSING_FIELDS':other_missing}
			sample_details.append({s["igoId"]: sample_map})

	request_details_map = {"REQUEST_ID": request_id, "PROJECT_ID": project_id, "IS_CMO_REQUEST": is_cmo_request, "TOTAL_NUM_SAMPLES": total_samples, "FAILED_NUM_SAMPLES": len(sample_details), "DETAILED_SAMPLE_ERRORS": sample_details}
	return request_details_map

def format_request_details_string(request_details_map):
	record = []
	for f in REQUEST_SUMMARY_REPORT_KEYS:
		if f == "DETAILED_SAMPLE_ERRORS":
			sample_details_string = []
			for s in request_details_map[f]:
				for sample_id,v in s.iteritems():
					if len(v["LABEL_GEN_MISSING_FIELDS"]) > 0:
						label_gen_fields_string = "LABEL_GEN_MISSING_FIELDS: " + ",".join(v["LABEL_GEN_MISSING_FIELDS"])
					else:
						label_gen_fields_string = ""
					if len(v["OTHER_ESSENTIAL_MISSING_FIELDS"]) > 0:
						other_fields_string = "OTHER_ESSENTIAL_MISSING_FIELDS: " ",".join(v["OTHER_ESSENTIAL_MISSING_FIELDS"])
					else:
						other_fields_string = ""
					
					to_add = "%s: %s; %s" % (sample_id, label_gen_fields_string, other_fields_string)
					sample_details_string.append(to_add)
			record.append(" | ".join(sample_details_string))
		else:
			record.append(str(request_details_map[f]))
	print("\t".join(record))


def load_request_details_from_log(filename):
	print("\t".join(REQUEST_SUMMARY_REPORT_KEYS))
	with open(filename, 'rU') as dfile:
		header = []
		for line in dfile.readlines():
			if not header:
				header = line.split('\t')
				continue
			data = line.split('\t')

			#logged status
			logged_status = data[1]

			request_json = json.loads(data[2])
			request_details_map = extract_request_details(request_json)
			request_details_map["LOGGED_REQUEST_STATUS"] = logged_status
			format_request_details_string(request_details_map)

def main():
	load_request_details_from_log(sys.argv[1])

if __name__ == '__main__':
	main()