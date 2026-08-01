#ifndef Foam_vtuneTaskTrace_H
#define Foam_vtuneTaskTrace_H

#include <cstdint>

namespace Foam
{

enum class vtuneTaskKind : std::uint8_t
{
    gaussSeidelSmooth,
    cellLimitedGradCalcGrad,
    lduMatrixResidual,
    lduMatrixAmul,
    gaussGradGradf,
    linearUpwindVCorrection
};


class vtuneTaskScope
{
    vtuneTaskKind kind_;
    std::uint64_t startNs_;
    long threadId_;
    bool active_;

public:

    explicit vtuneTaskScope(const vtuneTaskKind kind) noexcept;
    ~vtuneTaskScope() noexcept;

    vtuneTaskScope(const vtuneTaskScope&) = delete;
    void operator=(const vtuneTaskScope&) = delete;
};

} // End namespace Foam


#define FOAM_VTUNE_JOIN_IMPL(left, right) left##right
#define FOAM_VTUNE_JOIN(left, right) FOAM_VTUNE_JOIN_IMPL(left, right)
#define FOAM_VTUNE_TASK_SCOPE(kind) \
    ::Foam::vtuneTaskScope FOAM_VTUNE_JOIN(foamVtuneTaskScope_, __LINE__)(kind)

#endif

