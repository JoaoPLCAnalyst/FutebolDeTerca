import base64

def img_to_base64(uploaded_file):
    if uploaded_file is None:
        return None

    bytes_data = uploaded_file.read()
    encoded = base64.b64encode(bytes_data).decode("utf-8")

    return f"data:image/png;base64,{encoded}"
