package validation.mixin;

import dev.companion.minecraft.CompanionEntity;
import net.minecraft.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** CI-only probe after vanilla entity status handling. */
@Mixin(Entity.class)
abstract class EntityStatusTraceMixin {
    @Inject(method = "handleStatus", at = @At("TAIL"))
    private void ci$afterStatus(byte status, CallbackInfo ci) {
        if ((Object) this instanceof CompanionEntity companion && (status == 0 || status == 3)) {
            validation.CiClientValidation.trace("CI_SWING_STATUS_RECEIVED side="
                    + (companion.getWorld().isClient ? "CLIENT" : "SERVER")
                    + " status=" + status + " entityId=" + companion.getId()
                    + " uuid=" + companion.getUuid() + " age=" + companion.age
                    + " handSwinging=" + companion.handSwinging
                    + " handSwingTicks=" + companion.handSwingTicks
                    + " progress=" + companion.getHandSwingProgress(1.0F));
        }
    }
}
