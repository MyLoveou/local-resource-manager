export class EnumLabelMap {
  private forword: Record<string, string>
  private reverse: Record<string, string>
  constructor(labels: Record<string, string>) {
    this.forword = { ...labels }
    this.reverse = Object.fromEntries(Object.entries(labels).map(([key, value]) => [value, key]))
  }
  toLabel(value: string): string {
    return this.forword[value]
  }
  toValue(label: string, fallback = undefined): string {
    return this.reverse[label] ?? fallback
  }
}