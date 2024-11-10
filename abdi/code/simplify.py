from xml.dom import minidom
import os

# Paths for input and output files
input_svg_path = './provided floors/floor_5.svg'
output_svg_path = './simpler floors/floor5.svg'

# Check if input file exists
if not os.path.exists(input_svg_path):
    print(f"Input SVG file not found: {input_svg_path}")
else:
    # Load and parse the SVG file
    doc = minidom.parse(input_svg_path)

    # Find the layer with id "layer-oc6"
    layer_oc6 = None
    for g in doc.getElementsByTagName('g'):
        if g.getAttribute('id') == 'layer-oc5':
            layer_oc6 = g
            break

    # If the layer "layer-oc6" is found, remove everything else
    if layer_oc6:
        # Remove all elements that are not part of "layer-oc6"
        for element in list(doc.documentElement.childNodes):
            if element != layer_oc6 and element.nodeType == element.ELEMENT_NODE:
                doc.documentElement.removeChild(element)

        # Remove all text elements within the layer
        for text in layer_oc6.getElementsByTagName('text'):
            text.parentNode.removeChild(text)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_svg_path), exist_ok=True)

        # Save the modified SVG focusing solely on "layer-oc6" without text
        with open(output_svg_path, 'w') as f:
            doc.writexml(f)

        print("SVG file simplified and saved to:", output_svg_path)
    else:
        print(f"Layer 'layer-oc6' not found in the SVG file.")

    # Clean up resources
    doc.unlink()
