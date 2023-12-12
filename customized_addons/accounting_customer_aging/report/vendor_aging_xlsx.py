from odoo import models
from datetime import datetime


class CustomerAgingXlsx(models.AbstractModel):
    _name = 'report.accounting_customer_aging.report_vendor_aging_xls'
    _inherit = 'report.odoo_report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, vendors):
        
        workbook.default_format_properties = {'font_name': 'Arial', 'font_size': 10}
        worksheet = workbook.add_worksheet('Customer Aging Report')

        worksheet.set_column('A:A', 3)
        worksheet.set_column('B:B', 62)
        worksheet.set_row(3, 22.5)
        worksheet.set_row(5, 22.5)
        worksheet.set_column('B:H', 20)

        
        current_date = datetime.today().strftime("%m/%d/%Y")

        # Styles
        title_bold_center = workbook.add_format({'bold': True, "border": True, 'valign': 'vcenter', 'align': 'center', 'font_size': 20, 'font_name': 'Arial'})
        normal_bold_left = workbook.add_format({'bold': True, "border": True, 'valign': 'vcenter', 'align': 'left', 'font_size': 8.5, 'font_name': 'Arial'})
        normal_normal_left = workbook.add_format({'valign': 'vcenter', 'align': 'left', 'font_size': 8.5, 'border': True, 'font_name': 'Arial'})
        normal_normal_center = workbook.add_format({'valign': 'vcenter', 'align': 'center', 'font_size': 8.5, 'border': True, 'font_name': 'Arial'})
        table_header_left = workbook.add_format({'bold': True, 'valign': 'vcenter', 'align': 'left', 'border': True, 'text_wrap': True})
        table_header_center = workbook.add_format({'bold': True, 'valign': 'vcenter', 'align': 'center', 'font_size': 10, 'border': True, 'text_wrap': True})
        table_data_left = workbook.add_format({'valign': 'vcenter', 'border': True, 'align': 'left', 'font_size': 10, 'font_name': 'Arial'})
        table_data_center = workbook.add_format({'valign': 'vcenter', 'border': True, 'align': 'center', 'num_format': '$ #,##0.00', 'font_size': 10, 'font_name': 'Arial'})

        # Headers
        worksheet.merge_range('A1:B1', current_date, normal_normal_left)
        worksheet.merge_range('C1:H1', data["Company Name"], normal_normal_center)
        worksheet.merge_range('A2:H2', "Aged Partner Balance", title_bold_center)
        worksheet.merge_range('C3:H3', "Period Length (days):", normal_bold_left)
        worksheet.merge_range('C4:H4', "30", normal_normal_center)
        worksheet.merge_range('C5:H5', "Target Moves:", normal_bold_left)
        worksheet.merge_range('C6:H6', "All Posted Entries", normal_bold_left)
        worksheet.merge_range('A3:B3', "Aging Date:", normal_bold_left)
        worksheet.merge_range('A4:B4', data["Aging Date"], normal_normal_center)
        worksheet.merge_range('A5:B5', "Partner's:", normal_bold_left)
        worksheet.merge_range('A6:B6', "Payable Accounts", normal_normal_center)
        worksheet.write('C5', "Target Moves:", normal_bold_left)
        worksheet.write('C6', "All Posted Entries", normal_normal_center)
        
        age_table_head = ["Partners", "0-30", "30-60", "60-90", "90-120", "+120", "Total"]
        # Aging Table
        worksheet.merge_range('A7:B7', age_table_head[0], table_header_left)
        worksheet.write_row('C7', age_table_head[1:], table_header_center)
        totalAmountRange = ["Account Total"] + list(data["Total Amount by range"].values())
        worksheet.write("A8", "No.", workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'}))
        worksheet.write("B8", totalAmountRange[0], table_header_left)
        worksheet.write_row("C8", totalAmountRange[1:], table_data_center)

        row = 8
        num = 1

        for vendor in data:
            if vendor in ["data", "context", "token", "Company Name", "Total Amount by range", "Aging Date"]:
                pass
            else:
                row += 1
                vendor_list = [vendor] + list(data[vendor].values())
                worksheet.write(f'A{row}', num, table_header_center)
                worksheet.write(f"B{row}", vendor_list[0], table_data_left)    
                worksheet.write_row(f"C{row}", vendor_list[1:], table_data_center)
                num += 1