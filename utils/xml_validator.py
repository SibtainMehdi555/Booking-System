import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

def validate_areas_xml(xml_path: str) -> Tuple[bool, List[str]]:
    """
    Validates the areas XML file against the required specifications.
    Returns a tuple of (is_valid, list_of_errors)
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        errors = []
        
        # Get all areas
        areas = root.findall('area')
        
        # Check total number of areas
        if len(areas) < 10:
            errors.append("XML must contain at least 10 areas")
        
        # Count areas by capacity
        capacity_counts = {
            5: 0,
            10: 0,
            20: 0,
            50: 0
        }
        
        # Track unique daily costs
        daily_costs = set()
        
        for area in areas:
            try:
                capacity = int(area.get('capacity'))
                cost = float(area.get('cost_per_day'))
                
                # Count areas by capacity
                if capacity in capacity_counts:
                    capacity_counts[capacity] += 1
                
                # Track unique daily costs
                daily_costs.add(cost)
                
            except (ValueError, TypeError) as e:
                errors.append(f"Invalid capacity or cost value in area {area.get('id')}: {str(e)}")
        
        # Validate capacity requirements
        if capacity_counts[5] < 5:
            errors.append(f"Must have at least 5 areas with capacity 5 (found {capacity_counts[5]})")
        if capacity_counts[10] < 2:
            errors.append(f"Must have at least 2 areas with capacity 10 (found {capacity_counts[10]})")
        if capacity_counts[20] < 2:
            errors.append(f"Must have at least 2 areas with capacity 20 (found {capacity_counts[20]})")
        if capacity_counts[50] < 1:
            errors.append(f"Must have at least 1 area with capacity 50 (found {capacity_counts[50]})")
        
        # Validate daily costs
        if len(daily_costs) < 4:
            errors.append(f"Must have at least 4 different daily costs (found {len(daily_costs)})")
        
        return len(errors) == 0, errors
        
    except ET.ParseError as e:
        return False, [f"XML parsing error: {str(e)}"]
    except Exception as e:
        return False, [f"Unexpected error: {str(e)}"] 