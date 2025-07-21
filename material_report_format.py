from model.report.legacy import pp_utils

pp_utils.convert_format("baseline", "reporting_outputs/MESSAGEix-CA_baseline_obps_2025-07-14.xlsx", "material_pyom_report_2025-07-14.xlsx", OBPS_Credits=False)
pp_utils.material_convert_format("material_pyom_report.xlsx","material_IDEA_report.xlsx", legacy_report_path="reporting_outputs/output_pyam_MESSAGEix-CA_baseline_obps_2025-07-14.xlsx")#"material_pyom_report_2025-07-14.xlsx")

