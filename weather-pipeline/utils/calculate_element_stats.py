def calculate_element_stats(chunk_df, element_name):
    mask = (chunk_df['ELEMENT'] == element_name) & chunk_df['VALUE'].notna()
    if not mask.any():
        return 0, 0

    values = chunk_df.loc[mask, 'VALUE'] / 10.0
    valid_values = values[(values >= -100) & (values <= 100)]

    if valid_values.empty:
        return 0, 0

    return valid_values.sum(), len(valid_values)