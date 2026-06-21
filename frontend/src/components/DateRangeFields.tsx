import React from 'react';
import { isPresentDate, toMonthInputValue } from '../lib/dateUtils';

interface DateRangeFieldsProps {
  startDate: string;
  endDate: string;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
}

export function DateRangeFields({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
}: DateRangeFieldsProps) {
  const endIsPresent = isPresentDate(endDate);
  const startMonth = toMonthInputValue(startDate);

  return (
    <div className="date-range-fields">
      <input
        type="month"
        className="month-input"
        aria-label="Start month"
        value={startMonth}
        onChange={(e) => onStartChange(e.target.value)}
      />
      <span className="date-range-sep">–</span>
      {endIsPresent ? (
        <span className="date-range-present">Present</span>
      ) : (
        <input
          type="month"
          className="month-input"
          aria-label="End month"
          value={toMonthInputValue(endDate)}
          onChange={(e) => onEndChange(e.target.value)}
          min={startMonth || undefined}
        />
      )}
      <button
        type="button"
        className={`date-range-current${endIsPresent ? ' is-active' : ''}`}
        onClick={() => onEndChange(endIsPresent ? '' : 'Present')}
      >
        {endIsPresent ? 'Current role' : 'Mark current'}
      </button>
    </div>
  );
}
