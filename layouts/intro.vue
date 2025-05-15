<template>
  <div class="slidev-layout intro grid">
    <LayoutHeader />
    <div class="flex flex-col justify-center text-left">
      <slot></slot>
    </div>
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 text-[8px] text-gray-700 max-w-[90%] leading-tight text-center">
      <div class="font-bold mb-1">DISCLAIMER</div>
      FirstEnroll and AFE are not a subsidiary or affiliate of Zurich and use of FirstEnroll services are independent of, and not included within, the Hospital Indemnity  Policy or any other Zurich product or service. Zurich expressly disclaims any and all damages and other costs that may arise related to the use of or reliance upon the products, services, representations or warranties made by or on behalf of FirstEnroll or AFE.
    </div>
    <CornerCurves class="absolute bottom-0 right-0 transform scale-x--100" />
  </div>
</template>

<!-- 
<div class="font-bold mb-1">DISCLAIMER</div>
This is a brief description of coverage and is subject to the terms, conditions, limitations, and exclusions of the policy. Please see the policy and certificate for complete details. Coverage may not be available in all states.
<br/><br/>
<strong>FOR AGENT TRAINING USE ONLY</strong> - This document cannot be distributed to the public or used in any consumer solicitation.  -->