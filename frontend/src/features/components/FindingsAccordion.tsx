import type { ReactNode } from 'react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { FindingItem } from './FindingItem'
import type { Finding } from '../types/findings'

export interface FindingsAccordionGroup {
  key: string
  trigger: ReactNode
  findings: Finding[]
  itemLeading: (finding: Finding) => ReactNode
}

interface FindingsAccordionProps {
  groups: FindingsAccordionGroup[]
}

export function FindingsAccordion({ groups }: FindingsAccordionProps) {
  return (
    <Accordion type="multiple" className="w-full">
      {groups.map((group) => (
        <AccordionItem key={group.key} value={group.key}>
          <AccordionTrigger>{group.trigger}</AccordionTrigger>
          <AccordionContent>
            <ul className="flex flex-col gap-3">
              {group.findings.map((finding) => (
                <FindingItem key={finding.id} finding={finding} leading={group.itemLeading(finding)} />
              ))}
            </ul>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  )
}
