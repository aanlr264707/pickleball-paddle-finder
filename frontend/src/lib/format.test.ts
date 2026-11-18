import { describe, expect, it } from 'vitest'
import { toQuery } from '../api/client'
import { formatMetric, formatNumber, formatPrice, ordinal, paddleFamily, positionOnScale, roundToStep, stepFor } from './format'

describe('formatting', () => {
  it('formats numbers without needless decimals', () => {
    expect(formatNumber(116)).toBe('116')
    expect(formatNumber(7.96)).toBe('7.96')
    expect(formatNumber(2101)).toBe('2,101')
    expect(formatNumber(null)).toBe('–')
  })

  it('formats prices and metric values with units', () => {
    expect(formatPrice(169.99)).toBe('$169.99')
    expect(formatMetric({ key: 'power', unit: 'MPH' }, 56.2)).toBe('56.2 MPH')
    expect(formatMetric({ key: 'swing_weight', unit: 'units' }, 116)).toBe('116')
    expect(formatMetric({ key: 'price', unit: '$' }, 200)).toBe('$200.00')
  })

  it('writes ordinals', () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 100].map(ordinal)).toEqual(
      ['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '100th'])
  })
})

describe('paddle families', () => {
  it('folds the "+" types into their family', () => {
    expect(paddleFamily('Power +')).toBe('Power')
    expect(paddleFamily('All-Court')).toBe('All-Court')
    expect(paddleFamily('Control +')).toBe('Control')
  })
})

describe('slider math', () => {
  it('picks a step about a hundredth of the range', () => {
    expect(stepFor({ min: 95, max: 135 })).toBe(0.1)
    expect(stepFor({ min: 1500, max: 2500 })).toBe(10)
    expect(stepFor({ min: 7.2, max: 8.6 })).toBe(0.01)
  })

  it('rounds to the step and clamps positions', () => {
    expect(roundToStep(7.960000001, 0.01)).toBe(7.96)
    expect(positionOnScale({ min: 0, max: 10 }, 5)).toBe(50)
    expect(positionOnScale({ min: 0, max: 10 }, 20)).toBe(100)
  })
})

describe('toQuery', () => {
  it('drops empty values', () => {
    expect(toQuery({ q: 'joola', brand: '', page: 2, tournament_only: false, shape: null })).toBe('?q=joola&page=2')
    expect(toQuery({})).toBe('')
  })
})
