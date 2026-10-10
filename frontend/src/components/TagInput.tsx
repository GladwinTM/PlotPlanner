type TagInputProps = {
  label: string
  values: string[]
  placeholder?: string
  onChange: (values: string[]) => void
}

export function TagInput({ label, values, placeholder, onChange }: TagInputProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="text"
        placeholder={placeholder}
        defaultValue={values.join(', ')}
        key={values.join('|')}
        onBlur={(event) => {
          const next = event.target.value
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean)
          onChange(next)
        }}
      />
      <small>Comma-separated</small>
    </label>
  )
}
