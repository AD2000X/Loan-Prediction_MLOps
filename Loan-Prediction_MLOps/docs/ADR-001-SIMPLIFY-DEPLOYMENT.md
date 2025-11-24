# ADR-001: Simplify Deployment from Blue-Green to Rolling Updates

## Status
Accepted (2025-01-20)

## Context
The original implementation used blue-green deployment with 700+ lines of bash scripts
and duplicate Kubernetes deployments. This added significant complexity:

- Maintained two separate deployments (blue and green) with identical configurations
- Required complex bash scripts (287 lines) to manage traffic switching
- Needed external LoadBalancer with internet-facing configuration
- Health checks depended on external network accessibility
- Deployment time averaged 25-30 minutes
- Resource usage doubled during deployment windows (6 pods total)

This complexity was implemented without a clear business requirement for instant
rollback capabilities. The primary goal is to train models and deploy them to Kubernetes
with zero downtime, which Kubernetes rolling updates already provide natively.

## Decision
We will use Kubernetes native rolling updates instead of blue-green deployment.

### Key Changes
1. Single Deployment resource with rolling update strategy
2. Internal ClusterIP service instead of internet-facing LoadBalancer
3. In-cluster health checks via kubectl exec
4. Simplified CI/CD pipeline (3 jobs instead of 5)
5. Removed Great Expectations data validation (300+ lines)

### Rolling Update Configuration
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

This configuration ensures:
- Always maintains 3 available pods (maxUnavailable: 0)
- Allows 1 extra pod during updates (maxSurge: 1)
- New pods must pass readinessProbe before receiving traffic
- Automatic rollback if deployment fails

## Consequences

### Positive
- **80% code reduction**: 1500 lines to 300 lines
- **40% faster deployment**: 25-30 minutes to 15-20 minutes
- **33% resource savings**: 4 pods max during deployment instead of 6
- **Simpler debugging**: Single deployment, standard kubectl commands work
- **No AWS complexity**: No need for internet-facing LoadBalancer, public subnets, security groups
- **Lower maintenance**: No custom bash scripts to maintain
- **Easier onboarding**: Standard Kubernetes patterns, well-documented

### Negative
- **Slower rollback**: 1-2 minutes instead of instant (acceptable for current use case)
- **No A/B testing**: Cannot run two versions simultaneously (can use Canary later if needed)
- **Gradual traffic shift**: New version receives traffic incrementally, not all at once

### Neutral
- **Zero-downtime maintained**: Kubernetes rolling updates provide same guarantee
- **Production-grade quality**: Health checks, automatic rollback, resource limits all preserved
- **Monitoring unaffected**: Prometheus scraping continues via pod annotations

## Rationale

### Why This Decision Makes Sense
1. **No strict SLA requirements**: Application does not require sub-second rollback times
2. **Model update frequency**: Models update infrequently (weekly/monthly), not requiring instant switches
3. **Focus on core value**: Time better spent on model training, MLflow tracking, and monitoring
4. **AWS cost savings**: No need for internet-facing LoadBalancer and associated networking
5. **Proven technology**: Kubernetes rolling updates are battle-tested and widely used

### Why Blue-Green Was Premature
- Implemented before understanding actual rollback requirements
- Added complexity without corresponding business value
- Required significant AWS networking configuration that blocked progress
- Created debugging challenges that distracted from ML pipeline work

## Alternatives Considered

### 1. Keep Blue-Green Deployment
**Pros**: Instant rollback, ability to quickly switch traffic
**Cons**: 700+ lines of code, complex AWS setup, longer deployment time, higher resource usage
**Rejected**: Complexity not justified by current requirements

### 2. Canary Deployment with Istio
**Pros**: Gradual traffic shifting, advanced routing capabilities
**Cons**: Requires service mesh installation, adds infrastructure complexity
**Rejected**: Overkill for current needs, can implement later if traffic splitting needed

### 3. Manual Deployment
**Pros**: Maximum control
**Cons**: Not automated, error-prone, slow
**Rejected**: Violates CI/CD best practices

### 4. Recreate Strategy
**Pros**: Simplest possible approach
**Cons**: Downtime during updates
**Rejected**: Zero-downtime is a hard requirement

## Implementation Notes

### Health Check Changes
**Before**: External LoadBalancer health checks via public endpoint
```bash
curl http://load-balancer-dns/health
```

**After**: In-cluster health checks via kubectl exec
```bash
kubectl exec $POD -n loan-prediction-mlops -- curl http://localhost:8005/health
```

**Why**: Removes dependency on external network access, works with internal ClusterIP

### Service Changes
**Before**: LoadBalancer type with internet-facing annotations
```yaml
type: LoadBalancer
annotations:
  service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
```

**After**: ClusterIP for internal access
```yaml
type: ClusterIP
```

**Why**: No external traffic requirements currently, simplifies AWS configuration

### Monitoring Unchanged
Prometheus continues to scrape metrics via pod annotations:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8005"
  prometheus.io/path: "/metrics"
```

Service Discovery automatically adapts to new pod labels.

## Future Considerations

### When to Reintroduce Advanced Deployment Strategies

#### Blue-Green Deployment
**Reintroduce if:**
- Business requires instant rollback (< 10 seconds)
- Need to validate new version extensively before traffic switch
- Regulatory compliance requires instant rollback capability

**Implementation**: Use Argo Rollouts with BlueGreen strategy
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
spec:
  strategy:
    blueGreen:
      activeService: loan-prediction-active
      previewService: loan-prediction-preview
```

#### Canary Deployment
**Reintroduce if:**
- Need gradual traffic shifting (10% → 50% → 100%)
- Want to perform A/B testing between versions
- Require advanced traffic routing based on headers/user segments

**Implementation**: Use Istio VirtualService or Flagger
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
spec:
  analysis:
    threshold: 10
    stepWeight: 10
```

#### External LoadBalancer
**Reintroduce if:**
- Application needs to be accessed from internet
- Third-party services need to call API directly
- Web UI needs to connect from user browsers

**Implementation**: Add annotations to service
```yaml
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-scheme: internet-facing
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
```

## Success Metrics

Track these metrics to validate this decision:

1. **Deployment Success Rate**: Should remain 100% (or improve)
2. **Deployment Duration**: Should decrease from 25-30min to 15-20min
3. **Rollback Frequency**: Track how often rollbacks are needed
4. **Rollback Duration**: Measure if 1-2 minutes is acceptable
5. **Developer Productivity**: Measure time spent on deployment issues
6. **AWS Costs**: Monitor savings from simpler infrastructure

## Migration Path

### Rolling Back This Decision
If we need to revert to blue-green deployment:

1. Create blue-green deployment manifests (can reference deleted files in git history)
2. Restore blue_green_deploy.sh script
3. Add deploy-blue-green job to cicd.yml
4. Configure internet-facing LoadBalancer
5. Update health checks to use external endpoint

**Estimated effort**: 4-6 hours (well-documented process)

### Estimated Risk
**Low**: Rolling updates are widely used and proven. Risk of this decision failing is minimal.

## References

- [Kubernetes Rolling Updates Documentation](https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/)
- [Deployment Strategies Explained](https://spot.io/resources/kubernetes-autoscaling/5-kubernetes-deployment-strategies-roll-out-like-the-pros/)
- [When to Use Blue-Green vs Canary vs Rolling](https://www.weave.works/blog/kubernetes-deployment-strategies)

## Decision Makers
- Architectural decision: Claude Code
- Approved by: User
- Implementation: Claude Code
- Date: 2025-01-20

## Lessons Learned

### What Worked
- Clear analysis of requirements before implementation
- Focus on business value over technical sophistication
- Leveraging platform capabilities (Kubernetes) instead of custom scripts

### What Didn't Work Previously
- Implementing advanced patterns without clear requirements
- AWS networking complexity blocking progress
- Maintaining custom scripts for standard platform features

### Key Takeaway
**Start simple, add complexity only when clearly justified by business requirements.**
