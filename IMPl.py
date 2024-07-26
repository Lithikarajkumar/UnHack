import pandas as pd
import numpy as np

def parse_input(care_area_file, metadata_file):
    care_area_df = pd.read_csv(care_area_file, header=None)
    care_area_df.columns = ['Column1', 'Xmin', 'Xmax', 'Ymin', 'Ymax']
    metadata_df = pd.read_csv(metadata_file, skiprows=1, header=None)
    
    if metadata_df.shape[1] != 2:
        raise ValueError("Metadata file should have exactly two columns.")
    
    try:
        main_field_width = float(metadata_df.iloc[0, 0])
        sub_field_width = float(metadata_df.iloc[0, 1])
    except ValueError:
        raise ValueError("Metadata values must be numeric.")
    
    return care_area_df, main_field_width, sub_field_width

def place_main_fields(care_area_df, main_field_width):
    main_fields = []
    mf_id = 1
    for _, row in care_area_df.iterrows():
        x_min, x_max, y_min, y_max = row['Xmin'], row['Xmax'], row['Ymin'], row['Ymax']
        x_range = np.arange(x_min, x_max, main_field_width)
        y_range = np.arange(y_min, y_max, main_field_width)
        for x in x_range:
            for y in y_range:
                if x + main_field_width <= x_max and y + main_field_width <= y_max:
                    main_fields.append({
                        'ID': mf_id,
                        'Xmin': x,
                        'Xmax': x + main_field_width,
                        'Ymin': y,
                        'Ymax': y + main_field_width
                    })
                    mf_id += 1
    return main_fields

def place_sub_fields(main_fields, sub_field_width, care_area_df):
    sub_fields = []
    sf_id = 1
    
    # Convert care_area_df to a list of bounding boxes for clipping
    care_areas = [(row['Xmin'], row['Xmax'], row['Ymin'], row['Ymax']) for _, row in care_area_df.iterrows()]
    
    def clip_to_care_area(x_min, x_max, y_min, y_max, sf_id):
        clipped_sub_fields = []
        for (ca_xmin, ca_xmax, ca_ymin, ca_ymax) in care_areas:
            if x_min < ca_xmax and x_max > ca_xmin and y_min < ca_ymax and y_max > ca_ymin:
                # Clip coordinates to care area boundaries
                clipped_x_min = max(x_min, ca_xmin)
                clipped_x_max = min(x_max, ca_xmax)
                clipped_y_min = max(y_min, ca_ymin)
                clipped_y_max = min(y_max, ca_ymax)
                
                if clipped_x_min < clipped_x_max and clipped_y_min < clipped_y_max:
                    clipped_sub_fields.append({
                        'ID': sf_id,
                        'Xmin': clipped_x_min,
                        'Xmax': clipped_x_max,
                        'Ymin': clipped_y_min,
                        'Ymax': clipped_y_max,
                        'Main Field ID': mf['ID']
                    })
                    sf_id += 1
        return clipped_sub_fields, sf_id
    
    for mf in main_fields:
        x_min, x_max, y_min, y_max = mf['Xmin'], mf['Xmax'], mf['Ymin'], mf['Ymax']
        x = x_min
        while x < x_max:
            y = y_min
            while y < y_max:
                sub_x_max = min(x + sub_field_width, x_max)
                sub_y_max = min(y + sub_field_width, y_max)
                
                # Clip sub-field to care areas
                clipped_sub_fields, sf_id = clip_to_care_area(x, sub_x_max, y, sub_y_max, sf_id)
                sub_fields.extend(clipped_sub_fields)
                
                y = sub_y_max
            x = sub_x_max
    
    return sub_fields




def output_results(main_fields, sub_fields):
    main_field_df = pd.DataFrame(main_fields)
    sub_field_df = pd.DataFrame(sub_fields)
    main_field_df.to_csv('mainfields5.csv', index=False, header=False)
    sub_field_df.to_csv('subfields5.csv', index=False, header=False)

def verify_no_overlap(sub_fields):
    def is_overlapping(sf1, sf2):
        return not (sf1['Xmax'] <= sf2['Xmin'] or sf1['Xmin'] >= sf2['Xmax'] or
                    sf1['Ymax'] <= sf2['Ymin'] or sf1['Ymin'] >= sf2['Ymax'])
    
    # Create a list of all bounding boxes
    bounding_boxes = [(sf['Xmin'], sf['Xmax'], sf['Ymin'], sf['Ymax'], sf['ID']) for sf in sub_fields]
    
    # Sort bounding boxes by x_min to optimize overlap checks
    bounding_boxes.sort(key=lambda x: x[0])
    
    for i in range(len(bounding_boxes)):
        for j in range(i + 1, len(bounding_boxes)):
            if bounding_boxes[j][0] >= bounding_boxes[i][1]:
                break  # No need to check further if x_min of j is beyond x_max of i
            if is_overlapping(
                {'Xmin': bounding_boxes[i][0], 'Xmax': bounding_boxes[i][1], 'Ymin': bounding_boxes[i][2], 'Ymax': bounding_boxes[i][3]},
                {'Xmin': bounding_boxes[j][0], 'Xmax': bounding_boxes[j][1], 'Ymin': bounding_boxes[j][2], 'Ymax': bounding_boxes[j][3]}
            ):
                print(f"Overlap detected between Sub-Fields {bounding_boxes[i][4]} and {bounding_boxes[j][4]}")
                return False
    return True


def area(x_min, x_max, y_min, y_max):
    return (x_max - x_min) * (y_max - y_min)

def calculate_coverage_efficiency(care_area_df, sub_fields):
    care_areas = [(row['Xmin'], row['Xmax'], row['Ymin'], row['Ymax']) for _, row in care_area_df.iterrows()]
    total_care_area = sum(area(ca[0], ca[1], ca[2], ca[3]) for ca in care_areas)

    covered_area = 0
    for sf in sub_fields:
        covered_area += area(sf['Xmin'], sf['Xmax'], sf['Ymin'], sf['Ymax'])

    coverage_efficiency = covered_area / total_care_area
    print(f"Coverage Efficiency: {coverage_efficiency:.2f}")

def optimize_main_field_placement(care_area_df, main_field_width):
    main_fields = []
    
    care_area_df['Xmin'] = pd.to_numeric(care_area_df['Xmin'], errors='coerce')
    care_area_df['Xmax'] = pd.to_numeric(care_area_df['Xmax'], errors='coerce')
    care_area_df['Ymin'] = pd.to_numeric(care_area_df['Ymin'], errors='coerce')
    care_area_df['Ymax'] = pd.to_numeric(care_area_df['Ymax'], errors='coerce')
    
    main_field_width = float(main_field_width)
    
    mf_id = 1
    for _, row in care_area_df.iterrows():
        x_min, x_max, y_min, y_max = row['Xmin'], row['Xmax'], row['Ymin'], row['Ymax']
        while x_min < x_max:
            y_min_temp = y_min
            while y_min_temp < y_max:
                main_fields.append({
                    'ID': mf_id,
                    'Xmin': x_min,
                    'Xmax': x_min + main_field_width,
                    'Ymin': y_min_temp,
                    'Ymax': y_min_temp + main_field_width
                })
                y_min_temp += main_field_width
                mf_id += 1
            x_min += main_field_width
    
    return main_fields

def main():
    care_area_file = 'CareAreas.csv'
    metadata_file = 'metadata.csv'

    care_area_df, main_field_width, sub_field_width = parse_input(care_area_file, metadata_file)
    
    print("Care Area DataFrame Columns:", care_area_df.columns)
    
    main_fields = optimize_main_field_placement(care_area_df, main_field_width)
    sub_fields = place_sub_fields(main_fields, sub_field_width, care_area_df)
    output_results(main_fields, sub_fields)
    
    if verify_no_overlap(sub_fields):
        print("No overlap detected in Sub-Fields.")
    calculate_coverage_efficiency(care_area_df, sub_fields)

if __name__ == "__main__":
    main()
